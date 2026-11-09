// Runs the real Python pipeline in the browser with Pyodide. Built by build_site.py.
importScripts('https://cdn.jsdelivr.net/pyodide/v0.27.7/full/pyodide.js');
let py = null, runner = null, ready = null;

async function init() {
  postMessage({type: 'status', text: 'Loading the Python runtime (about 10 s the first time)...'});
  py = await loadPyodide();
  await py.loadPackage(['pydantic']);
  postMessage({type: 'status', text: 'Loading pipeline code and prompts...'});
  const manifest = await (await fetch('py/manifest.json', {cache: 'no-cache'})).json();
  for (const dir of manifest.dirs) py.FS.mkdirTree('/app/' + dir);
  for (const f of manifest.files) {
    const res = await fetch('py/' + f, {cache: 'no-cache'});
    if (!res.ok) throw new Error('could not load ' + f);
    py.FS.writeFile('/app/' + f, await res.text());
  }
  py.runPython("import sys, os; sys.path.insert(0, '/app'); os.chdir('/app')");
  runner = py.pyimport('browser_runner');
}

onmessage = async (e) => {
  const m = e.data;
  try {
    if (!ready) ready = init();
    await ready;
  } catch (err) {
    ready = null;
    postMessage({type: 'fatal', text: 'Could not start the Python runtime: ' + err});
    return;
  }
  if (m.type !== 'run') return;
  const runId = runner.new_run();
  const cfg = JSON.stringify(m.cfg);
  const started = performance.now();
  postMessage({type: 'start', runId: runId, n: m.items.length});
  for (let i = 0; i < m.items.length; i++) {
    postMessage({type: 'progress', i: i, label: m.items[i].label});
    let out;
    try { out = JSON.parse(runner.process_one(cfg, JSON.stringify(m.items[i].input))); }
    catch (err) { out = {error: String(err)}; }
    postMessage({type: 'result', i: i, label: m.items[i].label, out: out});
    if (out.error && /HTTP (401|403|404)/.test(out.error)) {
      postMessage({type: 'status', text: 'Stopped: the provider rejected the key or model. Check them and run again.'});
      break;
    }
  }
  const t = JSON.parse(runner.totals());
  postMessage({type: 'done', seconds: (performance.now() - started) / 1000, tokens_in: t.tokens_in,
               tokens_out: t.tokens_out, runId: t.run_id, audit: runner.audit_log()});
};
