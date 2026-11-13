// One view per step. Each shows the step's records in the form that is easiest to judge,
// and lets the reviewer change them in place when the step is waiting for review.

import { useState, type CSSProperties, type ReactNode } from "react";
import type { Axis, AxisSet, Backcast, Cluster, Critical, Driver, Narrative, Quadrant, Score, Signal, Values, ViewProps } from "./types";
import { Category, Editable, Linked, Links, Matrix, STEEPLE, Scale, patch } from "./ui";

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
      <div className="filters">
        <div className="strip" aria-hidden>
          {counts.map(([s, n]) => (
            <i key={s} style={{ flexGrow: n, background: STEEPLE[s], opacity: !category || category === s ? 1 : 0.25 }} />
          ))}
        </div>
        <div className="filter-row" role="group" aria-label="Filter by category">
          <button className={category ? "" : "on"} onClick={() => setCategory(null)}>All <b>{data.length}</b></button>
          {counts.map(([s, n]) => (
            <button key={s} className={category === s ? "on" : ""} onClick={() => setCategory(category === s ? null : s)}>
              <i className="sq" style={{ background: STEEPLE[s] }} />{s} <b>{n}</b>
            </button>
          ))}
          <span className="spacer" />
          <input type="search" placeholder="Search drivers" value={query} onChange={(e) => setQuery(e.target.value)} />
          {onChange && <button className="plain" onClick={add}>Add a driver</button>}
        </div>
      </div>
      {shown.length < data.length && <p className="hint">Showing {shown.length} of {data.length} drivers.</p>}
      <div className="ledger">
        {shown.map(([d, i]) => (
          <article className="entry" key={d.id}>
            <header className="entry-meta">
              <span className="mono">{d.id}</span>
              <Category value={d.steeple} onChange={onChange && ((steeple) => onChange(patch(data, i, { steeple })))} />
              {onChange && (
                <button className="icon" title="Delete this driver" onClick={() => onChange(data.filter((_, j) => j !== i))}>×</button>
              )}
            </header>
            <Editable className="item-title" value={d.name} onChange={onChange && ((name) => onChange(patch(data, i, { name })))} />
            <Editable className="item-text" value={d.description} placeholder="Describe the driver…" onChange={onChange && ((description) => onChange(patch(data, i, { description })))} />
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
      <p className="legend">
        {Object.entries(STEEPLE).map(([s, color]) => (
          <span key={s} className="cat"><i className="sq" style={{ background: color }} />{s}</span>
        ))}
      </p>
      <div className="ledger">
        {data.map((c, i) => (
          <article className="entry strong" key={i}>
            <header className="entry-meta">
              <span className="mono">{String(i + 1).padStart(2, "0")}</span>
              <span>{c.driver_ids.length} {c.driver_ids.length === 1 ? "driver" : "drivers"}</span>
            </header>
            <Editable className="item-title" value={c.name} onChange={onChange && ((name) => onChange(patch(data, i, { name })))} />
            <Editable className="item-text" value={c.rationale} placeholder="How are these drivers connected?" onChange={onChange && ((rationale) => onChange(patch(data, i, { rationale })))} />
            <ul className="members">
              {c.driver_ids.map((id) => (
                <li key={id} title={drivers[id]?.description}>
                  <i className="sq" style={{ background: STEEPLE[drivers[id]?.steeple] ?? "#777" }} />
                  <span>{drivers[id]?.name ?? id}</span>
                  {onChange && (
                    <span className="move" title="Move to another cluster">
                      move
                      <select value={i} onChange={(e) => move(id, i, Number(e.target.value))} aria-label={`Move ${drivers[id]?.name ?? id}`}>
                        {data.map((other, k) => <option key={k} value={k}>{other.name}</option>)}
                        <option value={-1}>A new cluster</option>
                      </select>
                    </span>
                  )}
                </li>
              ))}
            </ul>
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
      <div className="score-grid">
        <span className="axis-name down">Impact</span>
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
          <div className="score-row">
            <span className="tick" />
            {[1, 2, 3, 4, 5].map((n) => <span className="tick" key={n}>{n}</span>)}
          </div>
          <span className="axis-name">Uncertainty</span>
        </div>
      </div>
      <figcaption>
        <b>Where the drivers sit.</b> Each square counts the drivers with that impact and uncertainty; darker means more.
        The <mark>marked corner</mark> holds the critical uncertainties. Click a square to list its drivers.
      </figcaption>
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
        <p className="flag">
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
                    <p className="score-name">{s.name}</p>
                    {policy ? (
                      <p className="item-text"><Linked text={s.policy_evidence ?? ""} /></p>
                    ) : (
                      <Editable className="item-text" value={s.evidence} onChange={onChange && ((evidence) => set(i, { evidence }))} />
                    )}
                  </div>
                  <div className="meters">
                    <label>Impact <Scale label="Impact" value={s.impact} onChange={onChange && !policy ? (impact) => set(i, { impact }) : undefined} /></label>
                    <label>Uncertainty <Scale label="Uncertainty" value={s.uncertainty} onChange={onChange && !policy ? (uncertainty) => set(i, { uncertainty }) : undefined} /></label>
                    {policy && (
                      <label className="strong">Policy attention <Scale label="Policy attention" value={s.policy_attention} onChange={onChange && ((policy_attention) => set(i, { policy_attention }))} /></label>
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
    <div className="ledger">
      {data.map((c, i) => (
        <article className="entry strong" key={c.cluster}>
          <header className="entry-meta">
            <span>From the cluster <b>{c.cluster}</b></span>
            {onChange && <button className="icon" title="Remove this critical driver" onClick={() => onChange(data.filter((_, j) => j !== i))}>×</button>}
          </header>
          {onChange && (members[c.cluster]?.length ?? 0) > 1 ? (
            <select className="item-title pick" value={c.driver_id} onChange={(e) => swap(i, e.target.value)} title="Choose another driver of this cluster">
              {members[c.cluster].map((id) => (
                <option key={id} value={id}>
                  {scores[id].name} ({scores[id].impact}×{scores[id].uncertainty})
                </option>
              ))}
            </select>
          ) : (
            <div className="item-title">{c.name}</div>
          )}
          <div className="meters row">
            <label>Impact <Scale label="Impact" value={c.impact} /></label>
            <label>Uncertainty <Scale label="Uncertainty" value={c.uncertainty} /></label>
            <label>Policy attention <Scale label="Policy attention" value={c.policy_attention} /></label>
          </div>
          <Editable className="item-text" value={c.rationale} onChange={onChange && ((rationale) => onChange(patch(data, i, { rationale })))} />
        </article>
      ))}
    </div>
  );
}

// --- 6 · Axes -------------------------------------------------------------------------------

function AxisLine({ axis, steeple, onChange }: { axis: Axis; steeple?: string; onChange?: (axis: Axis) => void }) {
  return (
    <div className="axis">
      <p className="axis-head">
        <b>{axis.driver ?? axis.driver_id}</b> {steeple && <Category value={steeple} />}
      </p>
      <div className="axis-line">
        <Editable className="pole" value={axis.pole_a} onChange={onChange && ((pole_a) => onChange({ ...axis, pole_a }))} />
        <span className="span" aria-hidden />
        <Editable className="pole end" value={axis.pole_b} onChange={onChange && ((pole_b) => onChange({ ...axis, pole_b }))} />
      </div>
    </div>
  );
}

export function Axes({ data, values, onChange }: ViewProps<AxisSet>) {
  const steeple = Object.fromEntries((values.drivers ?? []).map((d) => [d.id, d.steeple]));
  return (
    <>
      {data.map((s, i) => (
        <section className="block" key={i}>
          <header className="block-head">
            <h2>Matrix {i + 1}</h2>
            {onChange && <button className="icon" title="Drop this matrix" onClick={() => onChange(data.filter((_, j) => j !== i))}>×</button>}
          </header>
          <AxisLine axis={s.x} steeple={steeple[s.x.driver_id]} onChange={onChange && ((x) => onChange(patch(data, i, { x })))} />
          <AxisLine axis={s.y} steeple={steeple[s.y.driver_id]} onChange={onChange && ((y) => onChange(patch(data, i, { y })))} />
          <div className="aside-text">
            <p className="label">Why these two together</p>
            <Editable className="item-text" value={s.rationale ?? ""} onChange={onChange && ((rationale) => onChange(patch(data, i, { rationale })))} />
          </div>
        </section>
      ))}
    </>
  );
}

// --- 6b · Signals ---------------------------------------------------------------------------

const STATUSES = ["dominant today", "established in places", "emerging", "weak signals", "no signal found"];
const EXISTS_TODAY = STATUSES.slice(0, 2);

/** How present a pole is today, as four segments: all filled is "dominant today", none is "no signal found". */
function Presence({ status }: { status: string }) {
  const at = STATUSES.indexOf(status);
  const level = at < 0 ? 0 : 4 - at;
  return (
    <span className="presence" aria-hidden>
      {[1, 2, 3, 4].map((n) => <i key={n} className={n <= level ? "on" : ""} />)}
    </span>
  );
}

export function Signals({ data, onChange, sendBack }: ViewProps<Signal>) {
  const sets = [...new Set(data.map((s) => s.axis_set))];
  return (
    <>
      <p className="legend">
        <span className="label">Present today</span>
        {STATUSES.map((s) => <span key={s} className="status"><Presence status={s} />{s}</span>)}
      </p>
      {sets.map((name, n) => {
        const rows = data.map((s, i) => [s, i] as const).filter(([s]) => s.axis_set === name);
        const drivers = [...new Set(rows.map(([s]) => s.driver))];
        return (
          <section className="block" key={name}>
            <header className="block-head"><h2>Matrix {n + 1}</h2></header>
            {drivers.map((driver) => {
              const poles = rows.filter(([s]) => s.driver === driver);
              const feedback =
                `The axis "${driver}" has low stretch: both of its poles already exist today (` +
                poles.map(([s]) => `"${s.pole}": ${s.status}`).join("; ") +
                "). Rewrite its poles as end-states for the horizon year, where at least one is a real break from what dominates today, or use another critical driver for this axis. Keep the other axes as they are.";
              return (
                <div className="axis" key={driver}>
                  <p className="axis-head"><b>{driver}</b></p>
                  {poles.every(([s]) => EXISTS_TODAY.includes(s.status)) && (
                    <p className="flag">
                      <b>Low stretch.</b> Both poles of this axis already exist today, so its scenarios may describe the present more than an open future.{" "}
                      {sendBack && (
                        <button className="link" onClick={() => sendBack("axes", feedback)}>Ask the AI for bolder poles (back to step 6)</button>
                      )}
                    </p>
                  )}
                  <div className="pair">
                    {poles.map(([s, i]) => (
                      <div className="signal" key={s.pole}>
                        <div className="pole">{s.pole}</div>
                        <label className="status">
                          <Presence status={s.status} />
                          {onChange ? (
                            <select value={s.status} onChange={(e) => onChange(patch(data, i, { status: e.target.value }))} aria-label="Present today">
                              {[...new Set([...STATUSES, s.status])].map((x) => <option key={x}>{x}</option>)}
                            </select>
                          ) : (
                            s.status
                          )}
                        </label>
                        <Editable className="item-text" value={s.signals} onChange={onChange && ((signals) => onChange(patch(data, i, { signals })))} />
                        {s.shift !== undefined && (
                          <>
                            <p className="label">What would have to change</p>
                            <Editable className="item-text" value={s.shift} onChange={onChange && ((shift) => onChange(patch(data, i, { shift })))} />
                          </>
                        )}
                        <Links sources={s.sources} />
                      </div>
                    ))}
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
        <section className="block" key={set.name}>
          <header className="block-head"><h2>Matrix {n + 1}</h2></header>
          <Matrix
            set={set}
            cell={(x, y) => {
              const i = data.findIndex((q) => q.axis_set === set.name && q.x_pole === x && q.y_pole === y);
              if (i < 0) return <span className="hint">No scenario</span>;
              return (
                <>
                  <Editable className="item-title" value={data[i].title} onChange={onChange && ((title) => onChange(patch(data, i, { title })))} />
                  <Editable className="item-text" value={data[i].sketch} onChange={onChange && ((sketch) => onChange(patch(data, i, { sketch })))} />
                </>
              );
            }}
          />
        </section>
      ))}
    </>
  );
}

// --- 8 · Narratives, 9 · Backcasting, and the final scenarios ------------------------------

/** Pick a scenario in its matrix (left); `detail` draws what the step adds to it (right). */
function Explorer({ values, detail }: { values: Values; detail: (set: AxisSet, quadrant: Quadrant) => ReactNode }) {
  const quadrants = values.quadrants ?? [];
  const sets = setsOf(values, quadrants);
  const [picked, setPicked] = useState(0);
  const [setName, setSetName] = useState(sets[0]?.name);
  const set = sets.find((s) => s.name === setName) ?? sets[0];
  if (!set) return <p className="hint">No scenarios yet.</p>;
  const mine = quadrants.filter((q) => q.axis_set === set.name);
  const quadrant = mine[picked] ?? mine[0];

  return (
    <div className="explorer">
      <div className="picker">
        {sets.length > 1 && (
          <div className="tabs" role="tablist">
            {sets.map((s, n) => (
              <button key={s.name} role="tab" aria-selected={s.name === set.name} className={s.name === set.name ? "active" : ""} onClick={() => { setSetName(s.name); setPicked(0); }}>
                Matrix {n + 1}
              </button>
            ))}
          </div>
        )}
        <Matrix
          compact
          set={set}
          cell={(x, y) => {
            const k = mine.findIndex((q) => q.x_pole === x && q.y_pole === y);
            if (k < 0) return null;
            return <button className={`scenario-pick ${k === picked ? "active" : ""}`} onClick={() => setPicked(k)}>{mine[k].title}</button>;
          }}
        />
        <p className="hint">Pick a scenario to read it.</p>
      </div>
      {quadrant && (
        <article className="scenario" key={`${set.name}-${quadrant.title}`}>
          <h2>{quadrant.title}</h2>
          <p className="poles">{quadrant.x_pole} <span aria-hidden>×</span> {quadrant.y_pole}</p>
          <p className="sketch">{quadrant.sketch}</p>
          {detail(set, quadrant)}
        </article>
      )}
    </div>
  );
}

/** Where a scenario's record sits in a step's list. */
const indexOf = (items: { axis_set?: string; title: string }[], set: AxisSet, q: Quadrant) =>
  items.findIndex((n) => n.title === q.title && (n.axis_set ?? set.name) === set.name);

function Voices({ narrative, onChange }: { narrative?: Narrative; onChange?: (narrative: Narrative) => void }) {
  if (!narrative) return null;
  return (
    <section className="part">
      <h3>Four people who live in it</h3>
      {Object.entries(narrative.personas).map(([persona, text]) => (
        <div className="voice-block" key={persona}>
          <p className="persona">The {persona}</p>
          <Editable className="voice" value={text} onChange={onChange && ((value) => onChange({ ...narrative, personas: { ...narrative.personas, [persona]: value } }))} />
        </div>
      ))}
    </section>
  );
}

function Pathway({ b, onChange }: { b?: Backcast; onChange?: (b: Backcast) => void }) {
  if (!b) return null;
  const evidence = (direction: string, title: string) => {
    const rows = b.signals.map((s, i) => [s, i] as const).filter(([s]) => s.direction === direction);
    return (
      <section className="part">
        <h3>{title} <span className="mono">{rows.length}</span></h3>
        {rows.map(([s, i]) => (
          <div className="evidence" key={i}>
            <p className="ev-meta"><b>{s.kind}</b>{s.strength}</p>
            <div>
              <Editable className="item-text" value={s.what} onChange={onChange && ((what) => onChange({ ...b, signals: patch(b.signals, i, { what }) }))} />
              <Links sources={[s.source]} />
            </div>
            {onChange && <button className="icon" title="Remove this signal" onClick={() => onChange({ ...b, signals: b.signals.filter((_, j) => j !== i) })}>×</button>}
          </div>
        ))}
        {!rows.length && <p className="hint">The searches found none.</p>}
      </section>
    );
  };

  return (
    <>
      <section className="part">
        <h3>The way back to today</h3>
        <ol className="pathway">
          {b.pathway.map((m, i) => (
            <li key={i}>
              <span className="mono">{m.year}</span>
              <Editable className="item-text" value={m.what} onChange={onChange && ((what) => onChange({ ...b, pathway: patch(b.pathway, i, { what }) }))} />
            </li>
          ))}
        </ol>
      </section>
      {evidence("towards", "Signs today that point towards it")}
      {evidence("against", "Signs today that point against it")}
      <section className="part">
        <h3>What the searches did not find</h3>
        <Editable className="item-text" value={b.gaps} onChange={onChange && ((gaps) => onChange({ ...b, gaps }))} />
      </section>
      <section className="part">
        <h3>Indicators to watch</h3>
        <p className="hint">Suggested by the AI, not verified.</p>
        <dl className="indicators">
          {b.indicators.map((x, i) => (
            <div key={i}><dt>{x.name}</dt><dd>{x.meaning}</dd></div>
          ))}
        </dl>
      </section>
    </>
  );
}

export function Narratives({ data, values, onChange }: ViewProps<Narrative>) {
  return (
    <Explorer
      values={values}
      detail={(set, q) => {
        const i = indexOf(data, set, q);
        return <Voices narrative={data[i]} onChange={onChange && ((n) => onChange(patch(data, i, n)))} />;
      }}
    />
  );
}

export function Backcasts({ data, values, onChange }: ViewProps<Backcast>) {
  return (
    <Explorer
      values={values}
      detail={(set, q) => {
        const i = indexOf(data, set, q);
        return <Pathway b={data[i]} onChange={onChange && ((b) => onChange(patch(data, i, b)))} />;
      }}
    />
  );
}

/** The finished run: every scenario with its four voices and its pathway back to today. */
export function Scenarios({ values }: { values: Values }) {
  return (
    <Explorer
      values={values}
      detail={(set, q) => (
        <>
          <Voices narrative={(values.narratives ?? [])[indexOf(values.narratives ?? [], set, q)]} />
          <Pathway b={(values.backcasts ?? [])[indexOf(values.backcasts ?? [], set, q)]} />
        </>
      )}
    />
  );
}
