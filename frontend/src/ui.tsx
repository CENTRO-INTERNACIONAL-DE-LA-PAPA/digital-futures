// Small building blocks shared by the step views.

import { useLayoutEffect, useRef, type ReactNode } from "react";
import type { AxisSet, Source } from "./types";

export const STEEPLE: Record<string, string> = {
  social: "#c2410c",
  technological: "#1d4ed8",
  economic: "#b45309",
  environmental: "#15803d",
  political: "#be185d",
  legal: "#6d28d9",
  ethical: "#0e7490",
};

/** Replace item `i` of a list with a changed copy. */
export function patch<T>(data: T[], i: number, change: Partial<T>): T[] {
  return data.map((item, j) => (j === i ? { ...item, ...change } : item));
}

/** Text that can be edited in place when `onChange` is given; plain text otherwise. */
export function Editable(props: { value: string; onChange?: (value: string) => void; className?: string; placeholder?: string }) {
  const { value, onChange, className = "", placeholder } = props;
  const ref = useRef<HTMLTextAreaElement>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "0";
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);
  if (!onChange) return <div className={className}>{value}</div>;
  return (
    <textarea
      ref={ref}
      rows={1}
      className={`editable ${className}`}
      value={value}
      placeholder={placeholder}
      title="Click to edit"
      onChange={(e) => onChange(e.target.value)}
    />
  );
}

/** A 1-5 score as five dots; click a dot to change the score. */
export function Dots(props: { value?: number; onChange?: (value: number) => void; label: string }) {
  const { value = 0, onChange, label } = props;
  return (
    <span className="dots" title={`${label}: ${value || "not scored"} of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" disabled={!onChange} className={n <= value ? "on" : ""} onClick={() => onChange?.(n)} aria-label={`${label} ${n}`} />
      ))}
      <b>{value || "–"}</b>
    </span>
  );
}

export function SteepleTag(props: { value: string; onChange?: (value: string) => void }) {
  const { value, onChange } = props;
  const style = { color: STEEPLE[value] ?? "#555", borderColor: STEEPLE[value] ?? "#555" };
  if (!onChange) return <span className="tag" style={style}>{value}</span>;
  return (
    <select className="tag" style={style} value={value} onChange={(e) => onChange(e.target.value)} title="Change the category">
      {Object.keys(STEEPLE).map((s) => <option key={s}>{s}</option>)}
    </select>
  );
}

const host = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};

export function Links({ sources }: { sources: Source[] }) {
  if (!sources?.length) return <p className="sources none">No source</p>;
  return (
    <p className="sources">
      {sources.map((s, i) => (
        <a key={i} href={s.url} target="_blank" rel="noreferrer" title={s.title}>{host(s.url)}</a>
      ))}
    </p>
  );
}

/** Text with its bare URLs turned into short links. */
export function Linked({ text }: { text: string }) {
  const parts = text.split(/(https?:\/\/[^\s)\]]+)/g);
  return (
    <>
      {parts.map((part, i) =>
        i % 2 ? <a key={i} href={part} target="_blank" rel="noreferrer">{host(part)}</a> : part,
      )}
    </>
  );
}

/** A 2x2 scenario matrix: X poles as columns, Y poles as rows; `cell` draws each quadrant. */
export function Matrix({ set, cell }: { set: AxisSet; cell: (xPole: string, yPole: string) => ReactNode }) {
  const xs = [set.x.pole_a, set.x.pole_b];
  const ys = [set.y.pole_a, set.y.pole_b];
  return (
    <div className="matrix">
      <div className="matrix-x">
        <span className="axis-label">{set.x.driver ?? set.x.driver_id}</span>
        <div className="matrix-poles">{xs.map((x) => <div key={x} className="pole">{x}</div>)}</div>
      </div>
      <div className="matrix-body">
        <span className="axis-label vertical">{set.y.driver ?? set.y.driver_id}</span>
        <div className="matrix-rows">
          {ys.map((y) => (
            <div className="matrix-row" key={y}>
              <div className="pole">{y}</div>
              {xs.map((x) => <div className="matrix-cell" key={x}>{cell(x, y)}</div>)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
