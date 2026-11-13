"""Run the real pipeline inside a web browser (Pyodide, in a Web Worker).

Used by the "Try it live" section of the demo site (docs/index.html). Only one
thing differs from `python pipeline.py`: how the model is called. Here the
browser sends each prompt straight to the provider (OpenAI, Anthropic or the
visitor's own Azure OpenAI resource) with the visitor's own API key (a synchronous XMLHttpRequest, which is allowed inside a Web Worker). The
rules, guardrails, escalation policy, routing and brief checks are the same
pipeline.process() the command line runs, loaded from the same files.

The key is passed in per call and never written anywhere.
"""
import contextlib
import io
import json
import re
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

import monday_client
import pipeline
from llm import DEFAULT_MODELS, LLMError, LLMResponse
from schemas import Application, ProcessedApplication
from site_render import card

ENDPOINTS = {"openai": "https://api.openai.com/v1/chat/completions",
             "anthropic": "https://api.anthropic.com/v1/messages"}
AZURE_API_VERSION = "2024-10-21"
# The key is only ever sent to an Azure OpenAI resource, never to an arbitrary URL.
AZURE_HOST = re.compile(r"^https://[a-z0-9][a-z0-9-]{0,62}\.(openai\.azure\.com|cognitiveservices\.azure\.com"
                        r"|services\.ai\.azure\.com)/?$")


def azure_url(endpoint: str, deployment: str) -> str:
    """Chat-completions URL for an Azure OpenAI deployment; rejects anything that is not an Azure host."""
    endpoint = (endpoint or "").strip().lower()
    if not AZURE_HOST.match(endpoint):
        raise LLMError("Azure endpoint must look like https://<resource>.openai.azure.com")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", deployment or ""):
        raise LLMError("Write the Azure deployment name in the Model box")
    return (f"{endpoint.rstrip('/')}/openai/deployments/{deployment}/chat/completions"
            f"?api-version={AZURE_API_VERSION}")
RETRY_STATUS = {0, 408, 409, 429, 500, 502, 503, 504, 529}  # 0 = network error

SAMPLES = {a.application_id: a for a in
           pipeline.load_applications(pipeline.ROOT / "data" / "crestview_client_applications.csv")[0]}
_auditor = None


def _wait(seconds: float):
    end = time.time() + seconds  # no real sleep in a worker without SharedArrayBuffer
    while time.time() < end:
        pass


def _error_text(body: str) -> str:
    try:
        err = json.loads(body).get("error", {})
        return str(err.get("message") or err)[:300]
    except (ValueError, AttributeError):
        return (body or "no response (network error or blocked by the browser)")[:300]


class BrowserLLM:
    """Same interface as llm.LLMClient: .provider, .model, .complete(prompt)."""

    def __init__(self, provider: str, model: str, key: str, endpoint: str = ""):
        self.provider = provider
        self.model = "mock" if provider == "mock" else (model or DEFAULT_MODELS[provider])
        self._key = key
        self._url = azure_url(endpoint, self.model) if provider == "azure" else ENDPOINTS.get(provider)

    def complete(self, prompt: str, max_retries: int = 3) -> LLMResponse:
        for attempt in range(1, max_retries + 1):
            start = time.time()
            status, body = self._post(prompt)
            if status == 200:
                resp = self._parse(body)
                resp.latency_ms = int((time.time() - start) * 1000)
                return resp
            if status not in RETRY_STATUS or attempt == max_retries:
                raise LLMError(f"{self.provider} HTTP {status}: {_error_text(body)}")
            _wait(2 ** attempt)
        raise LLMError("unreachable")

    def _post(self, prompt: str) -> tuple[int, str]:
        from js import XMLHttpRequest  # only exists inside the browser

        xhr = XMLHttpRequest.new()
        xhr.open("POST", self._url, False)
        xhr.setRequestHeader("content-type", "application/json")
        if self.provider in ("openai", "azure"):
            if self.provider == "azure":
                xhr.setRequestHeader("api-key", self._key)  # the deployment in the URL picks the model
            else:
                xhr.setRequestHeader("authorization", f"Bearer {self._key}")
            payload = {"model": self.model, "temperature": 0,
                       "response_format": {"type": "json_object"},
                       "messages": [{"role": "user", "content": prompt}]}
        else:
            xhr.setRequestHeader("x-api-key", self._key)
            xhr.setRequestHeader("anthropic-version", "2023-06-01")
            xhr.setRequestHeader("anthropic-dangerous-direct-browser-access", "true")
            payload = {"model": self.model, "max_tokens": 2000, "temperature": 0,
                       "messages": [{"role": "user", "content": prompt}]}
        try:
            xhr.send(json.dumps(payload))
        except Exception:  # NetworkError: offline, blocked, CORS
            return 0, ""
        return int(xhr.status), str(xhr.responseText or "")

    def _parse(self, body: str) -> LLMResponse:
        data = json.loads(body)
        if self.provider in ("openai", "azure"):
            usage = data.get("usage") or {}
            return LLMResponse(data["choices"][0]["message"].get("content") or "",
                               usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        usage = data.get("usage") or {}
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return LLMResponse(text, usage.get("input_tokens", 0), usage.get("output_tokens", 0))


def new_run() -> str:
    global _auditor
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    path = Path("/tmp/audit_log.jsonl")
    path.unlink(missing_ok=True)
    _auditor = pipeline.Auditor(path, run_id)
    return run_id


def totals() -> str:
    return json.dumps({"tokens_in": _auditor.input_tokens, "tokens_out": _auditor.output_tokens,
                       "run_id": _auditor.run_id})


def audit_log() -> str:
    path = Path("/tmp/audit_log.jsonl")
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _application(item: dict) -> Application:
    if item.get("sample_id"):
        return SAMPLES[item["sample_id"]]
    fields = dict(item)
    # one id per written application, so each becomes its own item on the board
    fields.setdefault("application_id", "CUSTOM-" + datetime.now().strftime("%m%d%H%M%S"))
    fields.setdefault("status", "New")
    fields.setdefault("submission_date", datetime.now().strftime("%Y-%m-%d"))
    return Application(**fields)


def _monday_transport(token: str):
    """POST to monday.com from inside the Web Worker (synchronous XHR)."""
    def send(payload: str):
        from js import XMLHttpRequest

        xhr = XMLHttpRequest.new()
        xhr.open("POST", monday_client.API_URL, False)
        xhr.setRequestHeader("content-type", "application/json")
        xhr.setRequestHeader("authorization", token)
        xhr.setRequestHeader("api-version", monday_client.API_VERSION)
        try:
            xhr.send(payload)
        except Exception:  # NetworkError; a 401 without CORS headers also lands here
            return 0, "", None
        return int(xhr.status), str(xhr.responseText or ""), xhr.getResponseHeader("retry-after")
    return send


def push_to_board(token: str, board_id: str, results_json: str, transport=None) -> str:
    """Write a finished run to an existing monday.com board with the same client the CLI uses.

    Maps the board's columns by title (nothing is added), updates items found by the
    application id in their name, creates the rest, and never touches a reviewer's status.
    """
    results = [ProcessedApplication(**r) for r in json.loads(results_json)
               if r.get("status") == "processed"]
    if not results:
        return json.dumps({"error": "Nothing to write: no processed results"})
    log = io.StringIO()
    monday_client.TRANSPORT = transport or _monday_transport(token)
    monday_client.SLEEP = _wait
    monday_client.CONFIG = Path(tempfile.gettempdir()) / "monday_board.json"
    try:
        with contextlib.redirect_stdout(log):
            monday_client.link(str(board_id).strip())
            url = monday_client.push_results(results)
        return json.dumps({"url": url, "count": len(results), "log": log.getvalue()})
    except BaseException as exc:  # SystemExit from link() included
        message = str(exc) or type(exc).__name__
        if "unreachable" in message:
            # monday.com answers a bad token with a 401 that has no CORS headers,
            # so the browser sees only a network error.
            message += ". The browser could not read monday.com's answer; the token is most likely wrong or expired."
        return json.dumps({"error": message, "log": log.getvalue()})
    finally:
        monday_client.TRANSPORT = None  # the token is not kept after the call


def process_one(cfg_json: str, item_json: str) -> str:
    """Run one application through pipeline.process(); return JSON for the page."""
    cfg, item = json.loads(cfg_json), json.loads(item_json)
    try:
        app = _application(item)
    except ValidationError as exc:
        problems = "; ".join(f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors())
        return json.dumps({"error": f"Application rejected at load: {problems}"})
    try:
        llm = BrowserLLM(cfg["provider"], cfg.get("model", ""), cfg.get("key", ""), cfg.get("endpoint", ""))
    except LLMError as exc:
        return json.dumps({"error": str(exc)})
    result = pipeline.process(app, llm, _auditor, pipeline.DEFAULT_PROMPT_VERSION)
    return json.dumps({"id": app.application_id, "status": result.status,
                       "tier": result.final_risk_tier, "error": result.error,
                       "html": card(result, app.description, "live"),
                       "result": result.model_dump(mode="json")})
