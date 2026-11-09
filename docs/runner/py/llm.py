"""A thin client over the model providers, so the pipeline does not care which one runs.

Providers (set LLM_PROVIDER, or leave it unset to use the first key found):
  anthropic  - ANTHROPIC_API_KEY
  openai     - OPENAI_API_KEY
  azure      - AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + LLM_MODEL (= deployment name)
  gemini     - GEMINI_API_KEY (free tier), via Gemini's OpenAI-compatible endpoint
  mock       - no network; deterministic output for testing the plumbing only

LLM_MODEL overrides the default model for the chosen provider.
In production at Crestview this would be `azure`: Azure OpenAI inside their own
Microsoft tenant, so client data never leaves their cloud boundary.
"""
import os
import time
from dataclasses import dataclass

DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-5-5",
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-2.5-flash",
    "azure": None,  # Azure uses your deployment name: set LLM_MODEL
}
KEY_VARS = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY", "azure": "AZURE_OPENAI_API_KEY"}
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Errors that will not fix themselves on retry.
NON_RETRYABLE = ("AuthenticationError", "PermissionDeniedError", "BadRequestError",
                 "NotFoundError")


class LLMError(Exception):
    pass


@dataclass
class LLMResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


def detect_provider() -> str:
    explicit = os.getenv("LLM_PROVIDER")
    if explicit:
        return explicit.lower()
    for provider, var in KEY_VARS.items():
        if os.getenv(var):
            return provider
    raise LLMError("No model provider configured. Set one of "
                   + ", ".join(KEY_VARS.values()) + " (or LLM_PROVIDER=mock).")


class LLMClient:
    def __init__(self, provider: str | None = None, model: str | None = None):
        self.provider = (provider or detect_provider()).lower()
        if self.provider == "mock":
            self.model = "mock"
            return
        if self.provider not in DEFAULT_MODELS:
            raise LLMError(f"Unknown LLM_PROVIDER '{self.provider}'")
        if not os.getenv(KEY_VARS[self.provider]):
            raise LLMError(f"{KEY_VARS[self.provider]} is not set")
        self.model = model or os.getenv("LLM_MODEL") or DEFAULT_MODELS[self.provider]
        if not self.model:
            raise LLMError("Set LLM_MODEL to your Azure OpenAI deployment name")

        if self.provider == "anthropic":
            import anthropic
            self._client = anthropic.Anthropic()
        elif self.provider == "azure":
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=os.environ["AZURE_OPENAI_API_KEY"],
                azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"))
        else:
            from openai import OpenAI
            if self.provider == "gemini":
                self._client = OpenAI(api_key=os.environ["GEMINI_API_KEY"],
                                      base_url=GEMINI_BASE_URL)
            else:
                self._client = OpenAI()

    def complete(self, prompt: str, max_retries: int = 3) -> LLMResponse:
        """Send one prompt, return the text. Retries transient failures with backoff."""
        for attempt in range(1, max_retries + 1):
            start = time.perf_counter()
            try:
                resp = self._call(prompt)
                resp.latency_ms = int((time.perf_counter() - start) * 1000)
                return resp
            except Exception as exc:  # network errors, rate limits, 5xx
                if type(exc).__name__ in NON_RETRYABLE or attempt == max_retries:
                    raise LLMError(f"{self.provider} call failed after {attempt} "
                                   f"tries: {type(exc).__name__}: {exc}") from exc
                time.sleep(2 ** attempt)
        raise LLMError("unreachable")

    def _call(self, prompt: str) -> LLMResponse:
        if self.provider == "anthropic":
            resp = self._client.messages.create(
                model=self.model, max_tokens=2000, temperature=0,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(block.text for block in resp.content if block.type == "text")
            return LLMResponse(text, resp.usage.input_tokens, resp.usage.output_tokens)
        # OpenAI, Azure OpenAI and Gemini share the chat-completions shape.
        # JSON mode guarantees syntactically valid JSON; the schema is still checked by us.
        resp = self._client.chat.completions.create(
            model=self.model, temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        usage = getattr(resp, "usage", None)
        return LLMResponse(resp.choices[0].message.content or "",
                           getattr(usage, "prompt_tokens", 0) or 0,
                           getattr(usage, "completion_tokens", 0) or 0)
