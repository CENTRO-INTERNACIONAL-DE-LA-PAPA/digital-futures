# Development plan

Living plan for the Digital Futures scenario agent. It turns the README directives and the
lessons from the 2025 probes (Marieke Veeger's notes, the FLW 2040 run, the Palmira workshop)
into a LangGraph application.

## Decisions taken (2026-11-10)

| Topic | Decision |
| --- | --- |
| Stack | LangGraph graph; deepagents for nodes 3 and 6; Python ≥ 3.12, `uv` |
| Persistence | Postgres as checkpointer (`PostgresSaver`) and long-term store (`PostgresStore`), via `docker compose` |
| Human in the loop | Every generating step is followed by a review step (LangGraph `interrupt`) |
| Node 4 | AI pre-scores with evidence, humans adjust. Split in two passes (4a impact + uncertainty, then 4b policy attention) |
| UI | Web app from the start (Streamlit), plus a terminal runner for development |
| Search | Tavily for web signals; Asta (`asta literature find`) for papers |
| Models | Through OpenRouter: Opus 5.5 (`anthropic/claude-opus-5.5`) for reasoning steps, Gemini 3.8 Flash (`google/gemini-3.8-flash`) for narratives; configurable by env var |
| Time frame | 2026 → 2065 |
| Axis sets | Their number follows the clusters, not a fixed 3 (exact rule settled in phase 6) |
| Narratives | For all quadrants |
| Drivers | Target about 80 per run (editable in the scope form) |
| Structured output | Native JSON schema (`ProviderStrategy`): Opus 5.5 rejects forced tool calls |

## Lessons from the probes → design rules

These rules become prompts and grading rubrics:

1. **Step by step, human between steps.** One step at a time, with a pause for review. Humans
   own the decisions; AI is input and inspiration.
2. **No CGIAR framing in the scope.** It narrows drivers to topics CGIAR already works on.
3. **Drivers: wide and granular.** Search across many fields of science, not only FLW; ask for
   more after the first, well-known batch. Every driver carries sources.
4. **Clusters must not be too broad.** Keep distinct drivers distinct; generic clusters
   ("technological innovation") lose the detail.
5. **Score impact and uncertainty first, policy attention second.** Asking for "least discussed"
   together with the rest pushed out relevant drivers.
6. **Axes:** each axis is one driver; its two poles are neutral (not good/bad, not more/less),
   each pole has a single characteristic, and both poles are states of the same driver. The two
   axes of a matrix come from different STEEPLE groups.
7. **Watch for bias** towards AI/tech-driven and optimistic futures.
8. **Quadrants:** develop all four, do not prioritise one.
9. **Narratives:** from the viewpoint of a farmer, a community leader, a scientist and a policy
   maker. Keep them short enough to read; dense output was draining.

## Graph

```
scope ─▶ drivers ⇄ review ─▶ clusters ⇄ review ─▶ score_impact ⇄ review ─▶ score_policy ⇄ review
      ─▶ critical ⇄ review ─▶ axes ⇄ review ─▶ quadrants ⇄ review ─▶ narratives ⇄ review ─▶ END
```

Each `review` node calls `interrupt()` with the step output. The human resumes with one of:

- `{"action": "approve"}`: keep the output, go on;
- `{"action": "edit", "data": ...}`: replace the output with an edited version, go on;
- `{"action": "revise", "feedback": "..."}`: send the step back to the AI with the feedback.

Generation and review are separate nodes so that resuming an interrupt never re-runs an LLM call.
With `hitl=False` the review nodes approve automatically, which gives the "Solo AI" and
"AI + pre-workshop drivers" arms of the working-paper design (seed drivers go in the scope).

| # | Node | Engine |
| --- | --- | --- |
| 1 | `scope` | No LLM: defaults or form input (theme, geography, current/horizon year, seed drivers) |
| 2 | `drivers` | Opus 5.5 + Tavily + Asta tools |
| 3 | `clusters` | deepagent + `RubricMiddleware` (rules 4) |
| 4a | `score_impact` | Opus 5.5: impact and uncertainty 1–5 per driver, with evidence |
| 4b | `score_policy` | Opus 5.5 + Tavily: attention in policy arenas 1–5, with evidence |
| 5 | `critical` | Opus 5.5: most uncertain, highest impact, then least discussed |
| 6 | `axes` | deepagent + `RubricMiddleware` (rule 6) |
| 7 | `quadrants` | Opus 5.5: four quadrants per axis set |
| 8 | `narratives` | Gemini: one narrative per quadrant, four personas |

### Node 4 operational definitions (to validate with Marieke)

- **Impact** = breadth (how many FLW subsystems it touches) × magnitude (size of change by the
  horizon year), justified with sources.
- **Uncertainty** = how far plausible trajectories diverge in the sources: sources that disagree
  on direction or speed score high; a consensus trend scores low.
- **Policy attention** = how present the driver is in policy arenas (national strategies,
  UN/FAO/IPCC processes, regional bodies), checked with targeted searches.

## Phases

| Phase | Content | Done when |
| --- | --- | --- |
| 0 ✅ | Repo setup: deps, `.env.example`, Postgres compose, `langgraph.json` | `uv sync` and `docker compose up` work |
| 1 ✅ | Skeleton: state, review loop, 8 stub nodes, Postgres persistence, terminal runner | A full run with simulated human answers passes in tests |
| 2 ✅ | Web app shell (Streamlit): scope form, review panel per step, thread resume | A human can drive the stub graph in the browser |
| 3 ✅ | Node 2 for real: Tavily + Asta tools, Opus 5.5 | Real drivers with sources |
| 4 | Node 3 deepagent clustering + rubric | Clusters pass rule 4 |
| 5 | Nodes 4a, 4b, 5 | Scores with evidence; human-adjustable table in the UI |
| 6 | Node 6 deepagent axes + rubric, node 7 | Axes pass rule 6; quadrants for each set |
| 7 | Node 8 narratives (Gemini) | Readable narratives per quadrant and persona |
| 8 | Research support: run log (timings, human edits), export to Markdown, experiment arms | Outputs usable for the working paper metrics |

## Open questions

- Exact rule linking clusters to axis sets (one set per pair of clusters holding a critical driver?).
