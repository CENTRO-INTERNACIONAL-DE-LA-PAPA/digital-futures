// Small building blocks shared by the step views.

import { Fragment, useLayoutEffect, useRef, type ReactNode } from "react";
import type { AxisSet, Source } from "./types";

export const STEEPLE: Record<string, string> = {
  social: "#c4572a",
  technological: "#2b59c3",
  economic: "#b0820f",
  environmental: "#2f7d4f",
  political: "#a8326b",
  legal: "#6a4bb5",
  ethical: "#1c7c8c",
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

/** A 1-5 score as five segments; click a segment to change the score. */
export function Scale(props: { value?: number; onChange?: (value: number) => void; label: string }) {
  const { value = 0, onChange, label } = props;
  return (
    <span className="scale" title={`${label}: ${value || "not scored"} of 5`}>
      {[1, 2, 3, 4, 5].map((n) => (
        <button key={n} type="button" disabled={!onChange} className={n <= value ? "on" : ""} onClick={() => onChange?.(n)} aria-label={`${label} ${n}`} />
      ))}
      <b>{value || "–"}</b>
    </span>
  );
}

/** A STEEPLE category: a square of its colour and its name; a menu when `onChange` is given. */
export function Category(props: { value: string; onChange?: (value: string) => void }) {
  const { value, onChange } = props;
  const square = <i className="sq" style={{ background: STEEPLE[value] ?? "#777" }} />;
  if (!onChange) return <span className="cat">{square}{value}</span>;
  return (
    <label className="cat" title="Change the category">
      {square}
      <select value={value} onChange={(e) => onChange(e.target.value)} aria-label="Category">
        {Object.keys(STEEPLE).map((s) => <option key={s}>{s}</option>)}
      </select>
    </label>
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

/** A 2x2 scenario matrix: X poles across, Y poles down, the two axes crossing in the middle.
 *  `cell` draws each quadrant. */
export function Matrix({ set, cell, compact }: { set: AxisSet; cell: (xPole: string, yPole: string) => ReactNode; compact?: boolean }) {
  const xs = [set.x.pole_a, set.x.pole_b];
  const ys = [set.y.pole_a, set.y.pole_b];
  return (
    <div className={`matrix ${compact ? "compact" : ""}`}>
      <p className="mx-key">
        <span><b>Across</b> {set.x.driver ?? set.x.driver_id}</span>
        <span><b>Down</b> {set.y.driver ?? set.y.driver_id}</span>
      </p>
      <span />
      {xs.map((x) => <div key={x} className="mx-pole across">{x}</div>)}
      {ys.map((y, r) => (
        <Fragment key={y}>
          <div className="mx-pole down">{y}</div>
          {xs.map((x, c) => <div className={`mx-cell r${r} c${c}`} key={x}>{cell(x, y)}</div>)}
        </Fragment>
      ))}
    </div>
  );
}
