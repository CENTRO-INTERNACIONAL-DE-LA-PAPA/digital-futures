import { useCallback, useEffect, useState } from "react";
import { api } from "./api";
import { STEPS, type Step } from "./steps";
import type { Run, RunMeta, Scope } from "./types";
import { CompareRuns, Report } from "./report";
import { Narratives } from "./views";

const same = (a: unknown, b: unknown) => JSON.stringify(a) === JSON.stringify(b);

export default function App() {
  const [runs, setRuns] = useState<RunMeta[]>([]);
  const [runId, setRunId] = useState(new URLSearchParams(location.search).get("run") ?? "");
  const [run, setRun] = useState<Run | null>(null);
  const [view, setView] = useState<string | null>(null); // the step on screen; null follows the run
  const [draft, setDraft] = useState<any[]>([]); // the reviewer's version of the step under review
  const [error, setError] = useState("");
  const [spent, setSpent] = useState<number | null>(null);
  const [showLog, setShowLog] = useState(false);

  const load = useCallback(async (id: string) => {
    const next = await api.run(id);
    setRun(next);
    setDraft(next.pending?.data ?? []);
    setView(null);
    api.activity().then((a) => setSpent(a.spent));
  }, []);

  const guard = (work: Promise<unknown>) => work.catch((e) => setError(String(e.message ?? e)));

  useEffect(() => {
    history.replaceState(null, "", runId ? `?run=${runId}` : location.pathname);
    setRun(null);
    setError("");
    guard(api.runs().then(setRuns));
    if (runId) guard(load(runId));
  }, [runId, load]);

  // While the AI works, ask for progress every second; reload the run when it is done.
  useEffect(() => {
    if (!run?.busy) return;
    const timer = setInterval(async () => {
      const p = await api.progress(run.id);
      if (p.busy) setRun((r) => r && { ...r, ...p });
      else guard(load(run.id));
    }, 1000);
    return () => clearInterval(timer);
  }, [run?.busy, run?.id, load]);

  const act = (request: Promise<unknown>) => guard(request.then(() => load(runId)));
  const scope = { theme: "", geography: "", current_year: 0, horizon_year: 0, ...run?.values.scope } as Scope;
  const finished = !!run && !run.busy && !run.pending && !run.failed && !!run.values.narratives?.length;
  const current = run?.pending?.step ?? run?.failed?.step ?? null;
  const working = STEPS.find((s) => s.name === run?.working) ?? null;
  const shown = view ?? current ?? (finished ? "scenarios" : null);
  const step = STEPS.find((s) => s.name === shown);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [shown, run?.busy]);

  return (
    <div className="app">
      <aside className="rail">
        <h1 className="brand">Digital Futures</h1>
        <select className="run-picker" value={runId} onChange={(e) => setRunId(e.target.value)} aria-label="Run">
          <option value="">＋ New run</option>
          {runs.map((r) => (
            <option key={r.id} value={r.id}>
              {r.created.slice(0, 16).replace("T", " ")} · {r.scope.geography ?? "Global South"} · {r.arm}
            </option>
          ))}
        </select>

        {run && (
          <nav className="stepper" aria-label="Steps">
            {STEPS.map((s) => {
              const done = run.done.includes(s.name) && working !== s;
              const state = run.failed?.step === s.name ? "failed" : working === s ? "working" : run.pending?.step === s.name ? "current" : done ? "done" : "todo";
              const size = (run.values[s.key] as unknown[] | undefined)?.length;
              return (
                <button key={s.name} className={`${state} ${shown === s.name ? "shown" : ""}`} disabled={state === "todo" || state === "working" || run.busy} onClick={() => setView(s.name)}>
                  <span className="bullet">{state === "done" ? "✓" : state === "failed" ? "!" : s.n}</span>
                  <span>
                    {s.title}
                    {done && size !== undefined && <small>{size} {s.key.replace("_", " ")}</small>}
                    {state === "current" && <small>waiting for your review</small>}
                    {state === "working" && <small>the AI is working…</small>}
                  </span>
                </button>
              );
            })}
            <button className={`${finished ? "done" : "todo"} ${shown === "scenarios" ? "shown" : ""}`} disabled={!finished} onClick={() => setView("scenarios")}>
              <span className="bullet">★</span>
              <span>Scenarios</span>
            </button>
            <button className={`done ${shown === "report" ? "shown" : ""}`} disabled={run.busy} onClick={() => setView("report")}>
              <span className="bullet">↓</span>
              <span>Report and metrics</span>
            </button>
          </nav>
        )}

        <button className="spend" onClick={() => setShowLog(true)} title="Open the activity log">
          {spent === null ? "Activity log" : <>AI spend so far <b>${spent.toFixed(2)}</b></>}
        </button>
      </aside>

      <main>
        {error && <div className="error" role="alert">{error} <button className="link" onClick={() => setError("")}>Dismiss</button></div>}
        {!runId ? (
          <NewRun onCreated={setRunId} onError={setError} />
        ) : !run ? (
          <p className="hint">Loading…</p>
        ) : run.busy ? (
          <Working run={run} step={working} />
        ) : run.failed && shown === run.failed.step ? (
          <Failed run={run} onRetry={() => act(api.retry(run.id))} />
        ) : step ? (
          <StepPage
            key={step.name}
            step={step}
            run={run}
            scope={scope}
            draft={draft}
            setDraft={setDraft}
            onDecision={(decision) => act(api.review(run.id, decision))}
            onReopen={() => act(api.reopen(run.id, step.name))}
          />
        ) : shown === "scenarios" ? (
          <>
            <Header n="★" title="Scenarios" what={`${run.values.quadrants?.length ?? 0} scenarios for ${scope.theme} in ${scope.geography}, ${scope.horizon_year}. AI-generated with human review: validate with domain experts before use.`} />
            <Narratives data={run.values.narratives ?? []} values={run.values} />
          </>
        ) : shown === "report" ? (
          <>
            <Header n="↓" title="Report and metrics" what="Download what this run produced, and see what it took: time, AI cost, and how much you changed." />
            <Report runId={run.id} />
          </>
        ) : (
          <p className="hint">This run has not produced anything yet.</p>
        )}
      </main>

      {showLog && <ActivityLog onClose={() => setShowLog(false)} />}
    </div>
  );
}

function Header({ n, title, what }: { n: string; title: string; what: string }) {
  return (
    <header className="page-head">
      <p className="eyebrow">{n === "★" || n === "↓" ? "Result" : `Step ${n}`}</p>
      <h1>{title}</h1>
      <p className="lede">{what}</p>
    </header>
  );
}

function StepPage(props: {
  step: Step;
  run: Run;
  scope: Scope;
  draft: any[];
  setDraft: (data: any[]) => void;
  onDecision: (decision: object) => void;
  onReopen: () => void;
}) {
  const { step, run, scope, draft, setDraft, onDecision, onReopen } = props;
  const [revising, setRevising] = useState(false);
  const [feedback, setFeedback] = useState("");
  const reviewing = run.pending?.step === step.name;
  const changed = reviewing && !same(draft, run.pending!.data);
  const next = STEPS[STEPS.indexOf(step) + 1];

  return (
    <>
      <Header n={step.n} title={step.title} what={step.what(scope)} />
      {reviewing ? (
        <p className="callout"><b>What to check.</b> {step.check}</p>
      ) : (
        <p className="callout past">
          You are looking at a finished step. To change it, <button className="link" onClick={onReopen}>reopen this step</button>.
          The steps after it will run again, and where nothing changed their saved results are reused at no cost.
        </p>
      )}

      <step.View data={reviewing ? draft : ((run.values[step.key] as any[]) ?? [])} values={run.values} onChange={reviewing ? setDraft : undefined} />

      {reviewing && (
        <footer className="actions">
          {revising ? (
            <div className="revise">
              <textarea autoFocus rows={3} placeholder="Tell the AI what to change in this step…" value={feedback} onChange={(e) => setFeedback(e.target.value)} />
              <button className="primary" disabled={!feedback.trim()} onClick={() => onDecision({ action: "revise", feedback: feedback.trim() })}>
                Send to the AI ({step.takes})
              </button>
              <button onClick={() => setRevising(false)}>Cancel</button>
            </div>
          ) : (
            <>
              <button className="primary" onClick={() => onDecision(changed ? { action: "edit", data: draft } : { action: "approve" })}>
                {changed ? "Save my changes and continue" : "Approve and continue"}
              </button>
              <span className="muted">{next ? `Next: ${next.n} · ${next.title} (${next.takes})` : "This is the last step."}</span>
              <span className="spacer" />
              {changed && <button onClick={() => setDraft(run.pending!.data)}>Undo my changes</button>}
              <button onClick={() => setRevising(true)}>Ask the AI to revise…</button>
            </>
          )}
        </footer>
      )}
    </>
  );
}

function Working({ run, step }: { run: Run; step: Step | null }) {
  const last = run.progress.at(-1);
  return (
    <section className="working">
      <div className="spinner" aria-hidden />
      <h1>{step ? `${step.n} · ${step.title}` : "Working…"}</h1>
      <p className="lede">{last?.message ?? "Starting…"}</p>
      <p className="muted">
        {Math.round(run.elapsed)} s so far{step && <> · this step usually takes {step.takes}</>}. You can leave this page; the work continues.
      </p>
      <ol className="progress-lines">
        {run.progress.slice(-12).map((p, i) => (
          <li key={i}><time>{Math.round(p.at)} s</time> {p.message}</li>
        ))}
      </ol>
    </section>
  );
}

function Failed({ run, onRetry }: { run: Run; onRetry: () => void }) {
  const step = STEPS.find((s) => s.name === run.failed!.step);
  return (
    <section className="working">
      <h1>{step ? `${step.n} · ${step.title}` : run.failed!.step} did not finish</h1>
      <p className="lede">Everything before this step is kept. Retry runs only this step again.</p>
      <pre className="error-detail">{run.failed!.error}</pre>
      <button className="primary" onClick={onRetry}>Retry this step</button>
    </section>
  );
}

function NewRun({ onCreated, onError }: { onCreated: (id: string) => void; onError: (message: string) => void }) {
  const [scope, setScope] = useState<Scope | null>(null);
  const [seeds, setSeeds] = useState("");
  const [hitl, setHitl] = useState(true);
  useEffect(() => {
    api.meta().then((m) => setScope(m.default_scope), (e) => onError(String(e.message ?? e)));
  }, []);
  if (!scope) return <p className="hint">Loading…</p>;

  const field = (label: string, key: keyof Scope, help?: string) => (
    <label>
      {label}
      <input
        type={typeof scope[key] === "number" ? "number" : "text"}
        value={scope[key] as string | number}
        onChange={(e) => setScope({ ...scope, [key]: typeof scope[key] === "number" ? Number(e.target.value) : e.target.value })}
      />
      {help && <small>{help}</small>}
    </label>
  );
  const start = () => {
    const seed_drivers = seeds.split("\n").map((s) => s.trim()).filter(Boolean);
    api.create({ ...scope, seed_drivers }, hitl).then((r) => onCreated(r.id), (e) => onError(String(e.message ?? e)));
  };

  return (
    <>
      <Header n="1" title="Scope of a new run" what="Set the theme, the place and the time frame. The AI then works step by step, and waits for your review after each step." />
      <form className="card form" onSubmit={(e) => { e.preventDefault(); start(); }}>
        {field("Theme", "theme")}
        {field("Geography", "geography")}
        <div className="pair">
          {field("Current year", "current_year")}
          {field("Horizon year", "horizon_year")}
        </div>
        <div className="pair">
          {field("Drivers to look for", "target_drivers", "About 80 gives a wide scan. Fewer is faster and cheaper.")}
          {field("Scenario matrices", "axis_sets", "Each matrix gives four scenarios, each told by four people.")}
        </div>
        <label>
          Drivers you already have (optional, one per line)
          <textarea rows={3} value={seeds} onChange={(e) => setSeeds(e.target.value)} placeholder="For example, drivers from a workshop" />
        </label>
        <label className="check">
          <input type="checkbox" checked={hitl} onChange={(e) => setHitl(e.target.checked)} /> Stop for my review after each step
        </label>
        <button className="primary">Start the scan (about 8 minutes)</button>
      </form>
      <CompareRuns onOpen={onCreated} />
    </>
  );
}

function ActivityLog({ onClose }: { onClose: () => void }) {
  const [log, setLog] = useState<{ lines: string[]; spent: number } | null>(null);
  useEffect(() => {
    api.activity().then(setLog);
  }, []);
  return (
    <div className="drawer-back" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>Activity log</h2>
          <button className="icon" onClick={onClose} title="Close">×</button>
        </header>
        <p className="hint">
          Every step and every AI call, with its duration, tokens and cost. AI spend recorded in this log: <b>${log?.spent.toFixed(2) ?? "…"}</b>
        </p>
        <pre>{log?.lines.slice().reverse().join("\n") ?? "Loading…"}</pre>
      </aside>
    </div>
  );
}
