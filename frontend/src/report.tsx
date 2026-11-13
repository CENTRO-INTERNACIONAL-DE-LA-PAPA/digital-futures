// The run report (downloads and metrics) and the comparison of all runs.

import { useEffect, useState } from "react";
import { api } from "./api";
import { STEPS } from "./steps";
import type { Metrics, RunRow } from "./types";

const minutes = (seconds: number | null) => (seconds === null ? "–" : seconds < 90 ? `${Math.round(seconds)} s` : `${(seconds / 60).toFixed(1)} min`);
const money = (usd: number) => `$${usd.toFixed(2)}`;

export function Report({ runId }: { runId: string }) {
  const [m, setM] = useState<Metrics | null>(null);
  useEffect(() => {
    api.metrics(runId).then(setM);
  }, [runId]);
  if (!m) return <p className="hint">Loading…</p>;
  const t = m.totals;

  return (
    <>
      <div className="downloads">
        <a className="button primary" href={`/api/runs/${runId}/export.md`}>Download the report (Markdown)</a>
        <a className="button" href={`/api/runs/${runId}/export.json`}>Download all data (JSON)</a>
        <span className="hint">The report holds the scenarios, the material behind them and this process record.</span>
      </div>

      <dl className="figures">
        <div><dd>{t.scenarios}</dd><dt>Scenarios</dt></div>
        <div><dd>{minutes(t.ai_seconds)}</dd><dt>AI time</dt></div>
        <div><dd>{money(t.cost)}</dd><dt>AI cost</dt></div>
        <div><dd>{minutes(t.review_seconds)}</dd><dt>Human review time</dt></div>
        <div><dd>{t.edited}</dd><dt>Reviews edited by hand</dt></div>
        <div><dd>{t.revised}</dd><dt>Reviews sent back to the AI</dt></div>
      </dl>
      <p className="hint">Experiment arm: <b>{m.arm}</b></p>
      {!m.complete && (
        <p className="flag">
          Some steps of this run ran before step times and costs were recorded, so the totals are partial. New runs, and steps you run from now on, are recorded in full.
        </p>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Step</th><th>Items</th><th>AI runs</th><th>Reused</th><th>AI time</th><th>AI cost</th>
              <th>Approved</th><th>Edited</th><th>Sent back</th><th>Review time</th><th>Kept as written</th>
            </tr>
          </thead>
          <tbody>
            {m.steps.map((r) => {
              const step = STEPS.find((s) => s.name === r.step);
              return (
                <tr key={r.step}>
                  <th>{step ? `${step.n} · ${step.title}` : r.step}</th>
                  <td>{r.items ?? "–"}</td>
                  {r.recorded ? (
                    <><td>{r.ai_runs}</td><td>{r.reused}</td><td>{minutes(r.ai_seconds)}</td><td>{money(r.cost)}</td></>
                  ) : (
                    <td colSpan={4} className="faint">ran before recording started</td>
                  )}
                  <td>{r.approved}</td><td>{r.edited}</td><td>{r.revised}</td><td>{minutes(r.review_seconds)}</td>
                  <td>{r.kept ? `${r.kept.unchanged} of ${r.kept.before}` : "–"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="hint">
        <b>Reused</b>: the step was reached again with nothing changed, so its saved result was used at no cost.{" "}
        <b>Review time</b> runs from the result being ready to your answer, and includes time away.{" "}
        <b>Kept as written</b>: items of the AI's output left untouched in your last edit.
      </p>
    </>
  );
}

const COLUMNS: [keyof RunRow, string][] = [
  ["created", "Started"], ["arm", "Arm"], ["geography", "Geography"], ["drivers", "Drivers"], ["clusters", "Clusters"],
  ["scenarios", "Scenarios"], ["finished", "Finished"], ["ai_seconds", "AI seconds"], ["cost", "AI cost (USD)"],
  ["review_seconds", "Review seconds"], ["edited", "Human edits"], ["revised", "Sent back"], ["id", "Run id"],
];

function csv(rows: RunRow[]): string {
  const quote = (v: unknown) => `"${String(v ?? "").replaceAll('"', '""')}"`;
  const lines = [COLUMNS.map(([, label]) => quote(label)), ...rows.map((r) => COLUMNS.map(([key]) => quote(r[key])))];
  return "data:text/csv;charset=utf-8," + encodeURIComponent(lines.map((l) => l.join(",")).join("\n"));
}

export function CompareRuns({ onOpen }: { onOpen: (id: string) => void }) {
  const [rows, setRows] = useState<RunRow[] | null>(null);
  useEffect(() => {
    api.compare().then(setRows);
  }, []);
  if (!rows?.length) return null;
  return (
    <section className="compare">
      <h2>Runs so far</h2>
      <p className="hint">
        One row per run, to compare the experiment arms. <a href={csv(rows)} download="digital-futures-runs.csv">Download as CSV</a>
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Started</th><th>Arm</th><th>Geography</th><th>Drivers</th><th>Scenarios</th><th>AI time</th><th>AI cost</th><th>Review time</th><th>Edits · sent back</th><th /></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <th>{r.created.slice(0, 16).replace("T", " ")}</th>
                <td>{r.arm}</td><td>{r.geography}</td><td>{r.drivers}</td><td>{r.scenarios}{r.finished ? " ✓" : ""}</td>
                <td>{minutes(r.ai_seconds)}</td><td>{money(r.cost)}</td><td>{minutes(r.review_seconds)}</td><td>{r.edited} · {r.revised}</td>
                <td><button className="link" onClick={() => onOpen(r.id)}>Open</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
