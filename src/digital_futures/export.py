"""Export a run as a Markdown report: scenarios first, then the material they were built from."""

from datetime import date

from digital_futures.metrics import summary

TITLES = {
    "drivers": "2 · Drivers of change",
    "clusters": "3 · Clusters",
    "score_impact": "4a · Impact and uncertainty",
    "score_policy": "4b · Attention in policy arenas",
    "critical": "5 · Critical drivers",
    "axes": "6 · Axes of uncertainty",
    "signals": "6b · Signals of plausibility",
    "quadrants": "7 · Quadrants",
    "narratives": "8 · Narratives",
}


def cell(text) -> str:
    """Text that is safe inside a Markdown table cell."""
    return str("" if text is None else text).replace("|", "\\|").replace("\n", " ")


def table(header: list[str], rows: list[list]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + " --- |" * len(header)]
    return lines + ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows] + [""]


def links(sources: list[dict]) -> str:
    return ", ".join(f"[{s['title'] or s['url']}]({s['url']})" for s in sources)


def duration(seconds: float | None) -> str:
    if seconds is None:
        return ""
    return f"{seconds:.0f} s" if seconds < 90 else f"{seconds / 60:.1f} min"


def scenarios(values: dict) -> list[str]:
    voices = {(n.get("axis_set"), n["title"]): n["personas"] for n in values.get("narratives", [])}
    out = []
    for n, s in enumerate(values.get("axis_sets", []), 1):
        out += [f"## Matrix {n}: {s['name']}", ""]
        for key in ("x", "y"):
            axis = s[key]
            out.append(f"- **Axis {key.upper()}: {axis.get('driver', axis['driver_id'])}.** {axis['pole_a']} ⟷ {axis['pole_b']}")
        out += ["", s.get("rationale", ""), ""]
        signals = [g for g in values.get("signals", []) if g["axis_set"] == s["name"]]
        if signals:
            out += ["### Signals seen today", ""]
            out += table(["Pole", "Status", "Signals", "Sources"], [[g["pole"], g["status"], g["signals"], links(g["sources"])] for g in signals])
        for q in (q for q in values.get("quadrants", []) if q["axis_set"] == s["name"]):
            out += [f"### {q['title']}", "", f"*{q['x_pole']} · {q['y_pole']}*", "", q["sketch"], ""]
            for persona, text in voices.get((s["name"], q["title"]), {}).items():
                out += [f"**{persona.capitalize()}.** {text}", ""]
    return out


def material(values: dict) -> list[str]:
    drivers = {d["id"]: d for d in values.get("drivers", [])}
    scores = {s["driver_id"]: s for s in values.get("scores", [])}
    out = []
    if values.get("critical"):
        out += ["## Critical drivers", ""]
        out += table(
            ["Cluster", "Critical driver", "Impact", "Uncertainty", "Policy attention", "Why"],
            [[c["cluster"], c["name"], c["impact"], c["uncertainty"], c["policy_attention"], c["rationale"]] for c in values["critical"]],
        )
    if values.get("clusters"):
        out += ["## Clusters", ""]
        for c in values["clusters"]:
            names = "; ".join(drivers[i]["name"] for i in c["driver_ids"] if i in drivers)
            out += [f"- **{c['name']}** ({len(c['driver_ids'])} drivers). {c['rationale']} *Drivers:* {names}"]
        out.append("")
    if drivers:
        out += ["## Drivers of change", ""]
        rows = []
        for d in drivers.values():
            s = scores.get(d["id"], {})
            rows.append([d["id"], d["name"], d["steeple"], d["description"], s.get("impact"), s.get("uncertainty"), s.get("policy_attention"), links(d["sources"])])
        out += table(["Id", "Driver", "Category", "Description", "Impact", "Uncertainty", "Policy attention", "Sources"], rows)
    return out


def process(values: dict) -> list[str]:
    m = summary(values)
    t = m["totals"]
    out = ["## Process record", "", f"Arm: **{m['arm']}**."]
    if not m["complete"]:
        out.append("Some steps ran before step times and costs were recorded; their AI columns are empty and the totals are partial.")
    out.append("")
    rows = []
    for r in m["steps"]:
        kept = f"{r['kept']['unchanged']} of {r['kept']['before']}" if r["kept"] else ""
        ai = [r["ai_runs"], r["reused"], duration(r["ai_seconds"]), f"${r['cost']:.2f}"] if r["recorded"] else [""] * 4
        rows.append([TITLES[r["step"]], r["items"], *ai, r["approved"], r["edited"], r["revised"], duration(r["review_seconds"]), kept])
    out += table(["Step", "Items", "AI runs", "Reused", "AI time", "AI cost", "Approved", "Edited", "Sent back", "Review time", "Items kept as written"], rows)
    out += [
        f"Totals: {t['scenarios']} scenarios; AI time {duration(t['ai_seconds'])}; AI cost ${t['cost']:.2f}; "
        f"human review time {duration(t['review_seconds']) or 'not recorded'}; {t['edited']} human edits; {t['revised']} steps sent back to the AI. "
        "Review time includes any time the reviewer was away.",
        "",
    ]
    return out


def to_markdown(values: dict) -> str:
    s = values.get("scope", {})
    head = [
        f"# Scenarios for {s.get('theme', '')} in {s.get('geography', '')}, {s.get('horizon_year', '')}",
        "",
        f"Exported on {date.today().isoformat()} from Digital Futures. Time frame: {s.get('current_year', '')} to {s.get('horizon_year', '')}.",
        "",
        "> This report was generated with AI (drivers, clusters, scores, axes, scenarios and narratives) and "
        "reviewed step by step by a human. The narratives are fiction that makes each scenario concrete, not "
        "forecasts. Validate the content with domain experts before using it.",
        "",
    ]
    return "\n".join(head + scenarios(values) + material(values) + process(values))
