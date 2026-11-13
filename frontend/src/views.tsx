// One view per step. Each shows the step's records in the form that is easiest to judge,
// and lets the reviewer change them in place when the step is waiting for review.

import { useState, type CSSProperties } from "react";
import type { Axis, AxisSet, Cluster, Critical, Driver, Narrative, Quadrant, Score, Signal, Values, ViewProps } from "./types";
import { Dots, Editable, Linked, Links, Matrix, STEEPLE, SteepleTag, patch } from "./ui";

// --- 2 · Drivers ----------------------------------------------------------------------------

export function Drivers({ data, onChange }: ViewProps<Driver>) {
  const [category, setCategory] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const counts = Object.keys(STEEPLE).map((s) => [s, data.filter((d) => d.steeple === s).length] as const);
  const shown = data
    .map((d, i) => [d, i] as const)
    .filter(([d]) => (!category || d.steeple === category) && `${d.name} ${d.description}`.toLowerCase().includes(query.toLowerCase()));

  const add = () => {
    const next = Math.max(0, ...data.map((d) => Number(d.id.slice(1)) || 0)) + 1;
    onChange?.([{ id: `d${next}`, name: "New driver", description: "", steeple: category ?? "social", sources: [] }, ...data]);
  };

  return (
    <>
      <div className="toolbar">
        <div className="steeple-bar" role="group" aria-label="Filter by category">
          {counts.map(([s, n]) => (
            <button
              key={s}
              className={category === s ? "active" : ""}
              style={{ flexGrow: Math.max(n, 3), background: STEEPLE[s] }}
              onClick={() => setCategory(category === s ? null : s)}
              title={`${n} ${s} drivers: click to filter`}
            >
              {s} <b>{n}</b>
            </button>
          ))}
        </div>
        <input type="search" placeholder="Search drivers…" value={query} onChange={(e) => setQuery(e.target.value)} />
        {onChange && <button onClick={add}>+ Add a driver</button>}
      </div>
      <p className="hint">
        Showing {shown.length} of {data.length} drivers{category && <> in <b>{category}</b></>}.
      </p>
      <div className="cards">
        {shown.map(([d, i]) => (
          <article className="card" key={d.id} style={{ borderTopColor: STEEPLE[d.steeple] }}>
            <header>
              <SteepleTag value={d.steeple} onChange={onChange && ((steeple) => onChange(patch(data, i, { steeple })))} />
              <span className="muted">{d.id}</span>
              {onChange && (
                <button className="icon" title="Delete this driver" onClick={() => onChange(data.filter((_, j) => j !== i))}>×</button>
              )}
            </header>
            <Editable className="card-title" value={d.name} onChange={onChange && ((name) => onChange(patch(data, i, { name })))} />
            <Editable className="card-text" value={d.description} placeholder="Describe the driver…" onChange={onChange && ((description) => onChange(patch(data, i, { description })))} />
            <Links sources={d.sources} />
          </article>
        ))}
      </div>
    </>
  );
}

// --- 3 · Clusters ---------------------------------------------------------------------------

export function Clusters({ data, values, onChange }: ViewProps<Cluster>) {
  const drivers = Object.fromEntries((values.drivers ?? []).map((d) => [d.id, d]));

  const move = (id: string, from: number, to: number) => {
    const next = data.map((c, i) => (i === from ? { ...c, driver_ids: c.driver_ids.filter((x) => x !== id) } : c));
    if (to < 0) next.push({ name: "New cluster", rationale: "", driver_ids: [id] });
    else next[to] = { ...next[to], driver_ids: [...next[to].driver_ids, id] };
    onChange?.(next.filter((c) => c.driver_ids.length));
  };

  return (
    <>
      <p className="hint">
        {data.length} clusters. The dot on each driver shows its category:{" "}
        {Object.entries(STEEPLE).map(([s, color]) => (
          <span key={s} className="legend"><i className="dot" style={{ background: color }} />{s}</span>
        ))}
      </p>
      <div className="cards wide">
        {data.map((c, i) => (
          <article className="card" key={i}>
            <header>
              <span className="count">{c.driver_ids.length}</span>
              <Editable className="card-title" value={c.name} onChange={onChange && ((name) => onChange(patch(data, i, { name })))} />
            </header>
            <Editable className="card-text" value={c.rationale} placeholder="How are these drivers connected?" onChange={onChange && ((rationale) => onChange(patch(data, i, { rationale })))} />
            <div className="chips">
              {c.driver_ids.map((id) => (
                <span className="chip" key={id} title={drivers[id]?.description}>
                  <i className="dot" style={{ background: STEEPLE[drivers[id]?.steeple] ?? "#999" }} />
                  {drivers[id]?.name ?? id}
                  {onChange && (
                    <span className="move" title="Move to another cluster">
                      ⇄
                      <select value={i} onChange={(e) => move(id, i, Number(e.target.value))} aria-label={`Move ${drivers[id]?.name ?? id}`}>
                        {data.map((other, k) => <option key={k} value={k}>{other.name}</option>)}
                        <option value={-1}>＋ A new cluster</option>
                      </select>
                    </span>
                  )}
                </span>
              ))}
            </div>
          </article>
        ))}
      </div>
    </>
  );
}

// --- 4a and 4b · Scores ---------------------------------------------------------------------

function ScoreMap({ data, cell, onPick }: { data: Score[]; cell: string | null; onPick: (cell: string | null) => void }) {
  const count = (impact: number, uncertainty: number) => data.filter((s) => s.impact === impact && s.uncertainty === uncertainty).length;
  const most = Math.max(1, ...[1, 2, 3, 4, 5].flatMap((i) => [1, 2, 3, 4, 5].map((u) => count(i, u))));
  return (
    <figure className="score-map">
      <figcaption>
        <b>Where the drivers sit.</b> Each square counts the drivers with that impact and uncertainty. The top right
        corner holds the critical uncertainties. Click a square to list its drivers.
      </figcaption>
      <div className="score-grid">
        <span className="axis-label vertical">Impact →</span>
        <div>
          {[5, 4, 3, 2, 1].map((impact) => (
            <div className="score-row" key={impact}>
              <span className="tick">{impact}</span>
              {[1, 2, 3, 4, 5].map((uncertainty) => {
                const n = count(impact, uncertainty);
                const key = `${impact}-${uncertainty}`;
                return (
                  <button
                    key={key}
                    disabled={!n}
                    className={`${cell === key ? "active" : ""} ${impact >= 4 && uncertainty >= 4 ? "hot" : ""}`}
                    style={{ "--fill": n / most } as CSSProperties}
                    onClick={() => onPick(cell === key ? null : key)}
                    title={`${n} drivers with impact ${impact} and uncertainty ${uncertainty}`}
                  >
                    {n || ""}
                  </button>
                );
              })}
            </div>
          ))}
          <div className="score-row ticks">
            <span className="tick" />
            {[1, 2, 3, 4, 5].map((n) => <span className="tick" key={n}>{n}</span>)}
          </div>
          <span className="axis-label">Uncertainty →</span>
        </div>
      </div>
    </figure>
  );
}

function Scores({ data, values, onChange, policy }: ViewProps<Score> & { policy: boolean }) {
  const [cell, setCell] = useState<string | null>(null);
  const index = Object.fromEntries(data.map((s, i) => [s.driver_id, i]));
  const inCell = (s: Score) => !cell || cell === `${s.impact}-${s.uncertainty}`;
  const groups = (values.clusters ?? []).map((c) => ({ name: c.name, ids: c.driver_ids.filter((id) => id in index) }));
  const grouped = new Set(groups.flatMap((g) => g.ids));
  const rest = data.filter((s) => !grouped.has(s.driver_id)).map((s) => s.driver_id);
  if (rest.length) groups.push({ name: "Not in a cluster", ids: rest });
  const set = (i: number, change: Partial<Score>) => onChange?.(patch(data, i, change));

  return (
    <>
      <ScoreMap data={data} cell={cell} onPick={setCell} />
      {cell && (
        <p className="hint">
          Showing only drivers with impact {cell[0]} and uncertainty {cell[2]}. <button className="link" onClick={() => setCell(null)}>Show all</button>
        </p>
      )}
      {groups.map((g) => {
        const rows = g.ids.map((id) => index[id]).filter((i) => inCell(data[i]));
        if (!rows.length) return null;
        return (
          <section className="score-group" key={g.name}>
            <h3>{g.name}</h3>
            {rows.map((i) => {
              const s = data[i];
              return (
                <div className="score-line" key={s.driver_id}>
                  <div>
                    <b>{s.name}</b>
                    {policy ? (
                      <p className="card-text"><Linked text={s.policy_evidence ?? ""} /></p>
                    ) : (
                      <Editable className="card-text" value={s.evidence} onChange={onChange && ((evidence) => set(i, { evidence }))} />
                    )}
                  </div>
                  <div className="meters">
                    <label>Impact <Dots label="Impact" value={s.impact} onChange={onChange && !policy ? (impact) => set(i, { impact }) : undefined} /></label>
                    <label>Uncertainty <Dots label="Uncertainty" value={s.uncertainty} onChange={onChange && !policy ? (uncertainty) => set(i, { uncertainty }) : undefined} /></label>
                    {policy && (
                      <label className="strong">Policy attention <Dots label="Policy attention" value={s.policy_attention} onChange={onChange && ((policy_attention) => set(i, { policy_attention }))} /></label>
                    )}
                  </div>
                </div>
              );
            })}
          </section>
        );
      })}
    </>
  );
}

export const ImpactScores = (props: ViewProps<Score>) => <Scores {...props} policy={false} />;
export const PolicyScores = (props: ViewProps<Score>) => <Scores {...props} policy />;

// --- 5 · Critical drivers -------------------------------------------------------------------

export function CriticalDrivers({ data, values, onChange }: ViewProps<Critical>) {
  const scores = Object.fromEntries((values.scores ?? []).map((s) => [s.driver_id, s]));
  const members = Object.fromEntries((values.clusters ?? []).map((c) => [c.name, c.driver_ids.filter((id) => id in scores)]));

  const swap = (i: number, id: string) => {
    const s = scores[id];
    onChange?.(patch(data, i, { driver_id: id, name: s.name, impact: s.impact, uncertainty: s.uncertainty, policy_attention: s.policy_attention ?? 0 }));
  };

  return (
    <div className="cards wide">
      {data.map((c, i) => (
        <article className="card" key={c.cluster}>
          <header>
            <span className="eyebrow">{c.cluster}</span>
            {onChange && <button className="icon" title="Remove this critical driver" onClick={() => onChange(data.filter((_, j) => j !== i))}>×</button>}
          </header>
          {onChange && (members[c.cluster]?.length ?? 0) > 1 ? (
            <select className="card-title pick" value={c.driver_id} onChange={(e) => swap(i, e.target.value)} title="Choose another driver of this cluster">
              {members[c.cluster].map((id) => (
                <option key={id} value={id}>
                  {scores[id].name} ({scores[id].impact}×{scores[id].uncertainty})
                </option>
              ))}
            </select>
          ) : (
            <div className="card-title">{c.name}</div>
          )}
          <div className="meters row">
            <label>Impact <Dots label="Impact" value={c.impact} /></label>
            <label>Uncertainty <Dots label="Uncertainty" value={c.uncertainty} /></label>
            <label>Policy attention <Dots label="Policy attention" value={c.policy_attention} /></label>
          </div>
          <Editable className="card-text" value={c.rationale} onChange={onChange && ((rationale) => onChange(patch(data, i, { rationale })))} />
        </article>
      ))}
    </div>
  );
}

// --- 6 · Axes -------------------------------------------------------------------------------

function AxisBar({ label, axis, steeple, onChange }: { label: string; axis: Axis; steeple?: string; onChange?: (axis: Axis) => void }) {
  return (
    <div className="axis">
      <p className="axis-head">
        <span className="eyebrow">{label}</span> <b>{axis.driver ?? axis.driver_id}</b> {steeple && <SteepleTag value={steeple} />}
      </p>
      <div className="axis-bar">
        <Editable className="pole" value={axis.pole_a} onChange={onChange && ((pole_a) => onChange({ ...axis, pole_a }))} />
        <span className="arrow" aria-hidden>⟷</span>
        <Editable className="pole" value={axis.pole_b} onChange={onChange && ((pole_b) => onChange({ ...axis, pole_b }))} />
      </div>
    </div>
  );
}

export function Axes({ data, values, onChange }: ViewProps<AxisSet>) {
  const steeple = Object.fromEntries((values.drivers ?? []).map((d) => [d.id, d.steeple]));
  return (
    <>
      {data.map((s, i) => (
        <article className="card set" key={i}>
          <header>
            <span className="eyebrow">Matrix {i + 1}</span>
            {onChange && <button className="icon" title="Drop this matrix" onClick={() => onChange(data.filter((_, j) => j !== i))}>×</button>}
          </header>
          <AxisBar label="Axis X" axis={s.x} steeple={steeple[s.x.driver_id]} onChange={onChange && ((x) => onChange(patch(data, i, { x })))} />
          <AxisBar label="Axis Y" axis={s.y} steeple={steeple[s.y.driver_id]} onChange={onChange && ((y) => onChange(patch(data, i, { y })))} />
          <p className="eyebrow">Why these two together</p>
          <Editable className="card-text" value={s.rationale ?? ""} onChange={onChange && ((rationale) => onChange(patch(data, i, { rationale })))} />
        </article>
      ))}
    </>
  );
}

// --- 6b · Signals ---------------------------------------------------------------------------

const STATUSES = ["happening now", "early signals", "no signal found"];

export function Signals({ data, onChange }: ViewProps<Signal>) {
  const sets = [...new Set(data.map((s) => s.axis_set))];
  return (
    <>
      <p className="hint">
        <span className="status happening-now">happening now</span> already the reality somewhere in scope ·{" "}
        <span className="status early-signals">early signals</span> proposals, pilots, lobbying, disputes ·{" "}
        <span className="status no-signal-found">no signal found</span> the searches found nothing relevant
      </p>
      {sets.map((name, n) => {
        const rows = data.map((s, i) => [s, i] as const).filter(([s]) => s.axis_set === name);
        const drivers = [...new Set(rows.map(([s]) => s.driver))];
        return (
          <article className="card set" key={name}>
            <header><span className="eyebrow">Matrix {n + 1}</span></header>
            {drivers.map((driver) => (
              <div key={driver}>
                <p className="axis-head"><b>{driver}</b></p>
                <div className="pair">
                  {rows.filter(([s]) => s.driver === driver).map(([s, i]) => (
                    <div className="signal" key={s.pole}>
                      {onChange ? (
                        <select className={`status ${s.status.replaceAll(" ", "-")}`} value={s.status} onChange={(e) => onChange(patch(data, i, { status: e.target.value }))}>
                          {STATUSES.map((x) => <option key={x}>{x}</option>)}
                        </select>
                      ) : (
                        <span className={`status ${s.status.replaceAll(" ", "-")}`}>{s.status}</span>
                      )}
                      <div className="pole">{s.pole}</div>
                      <Editable className="card-text" value={s.signals} onChange={onChange && ((signals) => onChange(patch(data, i, { signals })))} />
                      <Links sources={s.sources} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </article>
        );
      })}
    </>
  );
}

// --- 7 · Quadrants --------------------------------------------------------------------------

/** The sets of axes, rebuilt from the quadrants when the run has none (older runs). */
function setsOf(values: Values, quadrants: Quadrant[]): AxisSet[] {
  const names = [...new Set(quadrants.map((q) => q.axis_set))];
  return names.map((name) => {
    const known = values.axis_sets?.find((s) => s.name === name);
    if (known) return known;
    const mine = quadrants.filter((q) => q.axis_set === name);
    const [xa, xb = ""] = [...new Set(mine.map((q) => q.x_pole))];
    const [ya, yb = ""] = [...new Set(mine.map((q) => q.y_pole))];
    return { name, x: { driver_id: "X", pole_a: xa, pole_b: xb }, y: { driver_id: "Y", pole_a: ya, pole_b: yb } };
  });
}

export function Quadrants({ data, values, onChange }: ViewProps<Quadrant>) {
  return (
    <>
      {setsOf(values, data).map((set, n) => (
        <article className="card set" key={set.name}>
          <header><span className="eyebrow">Matrix {n + 1}</span></header>
          <Matrix
            set={set}
            cell={(x, y) => {
              const i = data.findIndex((q) => q.axis_set === set.name && q.x_pole === x && q.y_pole === y);
              if (i < 0) return <span className="muted">No scenario</span>;
              return (
                <>
                  <Editable className="card-title" value={data[i].title} onChange={onChange && ((title) => onChange(patch(data, i, { title })))} />
                  <Editable className="card-text" value={data[i].sketch} onChange={onChange && ((sketch) => onChange(patch(data, i, { sketch })))} />
                </>
              );
            }}
          />
        </article>
      ))}
    </>
  );
}

// --- 8 · Narratives, and the final scenarios ------------------------------------------------

export function Narratives({ data, values, onChange }: ViewProps<Narrative>) {
  const quadrants = values.quadrants ?? [];
  const sets = setsOf(values, quadrants);
  const [picked, setPicked] = useState(0);
  const [setName, setSetName] = useState(sets[0]?.name);
  const set = sets.find((s) => s.name === setName) ?? sets[0];
  if (!set) return <p className="hint">No scenarios yet.</p>;

  const mine = quadrants.filter((q) => q.axis_set === set.name);
  const quadrant = mine[picked] ?? mine[0];
  const i = data.findIndex((n) => n.title === quadrant?.title && (n.axis_set ?? set.name) === set.name);
  const narrative = data[i];

  return (
    <>
      {sets.length > 1 && (
        <div className="tabs">
          {sets.map((s, n) => (
            <button key={s.name} className={s.name === set.name ? "active" : ""} onClick={() => { setSetName(s.name); setPicked(0); }}>
              Matrix {n + 1}
            </button>
          ))}
        </div>
      )}
      <div className="explorer">
        <div>
          <p className="hint">Pick a scenario in the matrix.</p>
          <Matrix
            set={set}
            cell={(x, y) => {
              const k = mine.findIndex((q) => q.x_pole === x && q.y_pole === y);
              if (k < 0) return null;
              return <button className={`scenario-pick ${k === picked ? "active" : ""}`} onClick={() => setPicked(k)}>{mine[k].title}</button>;
            }}
          />
        </div>
        {quadrant && (
          <article className="card scenario">
            <h2>{quadrant.title}</h2>
            <p className="poles"><span className="pole">{quadrant.x_pole}</span><span className="pole">{quadrant.y_pole}</span></p>
            <p className="card-text">{quadrant.sketch}</p>
            <div className="voices">
              {Object.entries(narrative?.personas ?? {}).map(([persona, text]) => (
                <section key={persona}>
                  <p className="eyebrow">{persona}</p>
                  <Editable className="voice" value={text} onChange={onChange && ((value) => onChange(patch(data, i, { personas: { ...narrative.personas, [persona]: value } })))} />
                </section>
              ))}
            </div>
          </article>
        )}
      </div>
    </>
  );
}
