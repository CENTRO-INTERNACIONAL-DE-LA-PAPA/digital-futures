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
| UI | React app (`frontend/`, Vite + TypeScript, no UI library) on a small FastAPI API (`api.py`); one purpose-built view per step. Replaced the Streamlit prototype on 2026-11-13. A terminal runner stays for development. Visual design: a working paper, not a dashboard (serif for reading, hairlines instead of cards, one highlighter colour for what needs the reviewer); the rules are at the top of `frontend/src/styles.css` |
| Saved results | Each step's result is saved per run under a hash of its inputs. Going back and continuing without changes reuses it (human edits included) at no AI cost |
| Signals (6b) | After the axes: one web search per pole and one paper search per axis. The AI places each pole on a scale of distance from today (dominant today, established in places, emerging, weak signals, no signal found), says what would have to change for it to prevail, and cites only links from the results. An axis whose two poles both exist today is flagged as low stretch and can be sent back to step 6. Quadrants build on the signals |
| Axes stretch | Poles are end-states for the horizon year; at least one pole per axis must be a real break from what dominates today (prompt rule and rubric criterion 8, added 2026-11-13; to confirm with Marieke) |
| Backcasting (9) | Last step. Per scenario: a pathway of four milestones back from the horizon year, then news, web and paper searches for the first steps; the AI picks signals of change from the results only, for and against the scenario, plus what was not found and indicators to watch (unverified) |
| Saved results and prompts | The hash of a step's saved result includes the step's own code, so a changed prompt is not served old results |
| Search | Tavily for web signals; Asta (`asta literature find`) for papers |
| Models | Through OpenRouter: Gemini 3.8 Flash (`google/gemini-3.8-flash`) for reasoning, narratives and grading (chosen 2026-11-10); configurable by env var. Claude models also work for the agents but not as the grader |
| Time frame | 2026 → 2065 |
| Axis sets | Every cluster gives one candidate axis (its critical driver). The AI pairs candidates into sets; how many sets is a run setting (default 3, chosen 2026-11-13, to confirm with Marieke) |
| Narratives | For all quadrants |
| Drivers | Target about 80 per run (editable in the scope form) |
| Critical drivers | One per cluster: highest impact × uncertainty, ties broken by lower policy attention; the AI explains each pick |
| Policy attention (4b) | One Tavily search per driver; the score cites the links found |
| Structured output | Native JSON schema: `config.chat_model` marks models as supporting it, because Claude models reject forced tool calls |
| Rubric grader | Gemini 3.8 Flash (`DF_GRADER_MODEL`): Anthropic models reject the grader schema's `oneOf` |

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
      ─▶ critical ⇄ review ─▶ axes ⇄ review ─▶ signals ⇄ review ─▶ quadrants ⇄ review
      ─▶ narratives ⇄ review ─▶ backcast ⇄ review ─▶ END
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
| 2 | `drivers` | Reasoning model + Tavily + Asta tools |
| 3 | `clusters` | deepagent + `RubricMiddleware` (rules 4) |
| 4a | `score_impact` | Reasoning model: impact and uncertainty 1–5 per driver, with evidence |
| 4b | `score_policy` | Reasoning model + Tavily: attention in policy arenas 1–5, with evidence |
| 5 | `critical` | Reasoning model: most uncertain, highest impact, then least discussed |
| 6 | `axes` | deepagent + `RubricMiddleware` (rules 6 and 7): sets of two axes, each with two neutral poles |
| 6b | `signals` | Tavily per pole + Asta per axis, then the reasoning model: is each pole already visible today? |
| 7 | `quadrants` | Reasoning model: four quadrants per axis set (title and short sketch), one question per set |
| 9 | `backcast` | Reasoning model twice per scenario (pathway and searches; then signals from the results), Tavily web + news, Asta |
| 8 | `narratives` | Narrative model: one question per quadrant, four first-person accounts of 100–140 words |

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
| 3 ✅ | Node 2 for real: Tavily + Asta tools | Real drivers with sources |
| 4 ✅ | Node 3 deepagent clustering + rubric | Clusters pass rule 4 |
| 5 ✅ | Nodes 4a, 4b, 5 | Scores with evidence; human-adjustable table in the UI |
| 6 ✅ | Node 6 deepagent axes + rubric, node 7 | Axes pass rule 6; quadrants for each set |
| 7 ✅ | Node 8 narratives (Gemini) | Readable narratives per quadrant and persona |
| 7b ✅ | Saved step results, signals step (6b), React app replacing Streamlit | Going back costs nothing; every step has a readable, editable view |
| 7c ✅ | Axes that stretch beyond today, signals as distance from today, backcasting step (9) | Few poles are "dominant today"; every scenario has a pathway and cited signals |
| 8 ✅ | Research support: run log (timings, human edits), export to Markdown, experiment arms | Outputs usable for the working paper metrics |

## Open questions

- Axis sets: is "one candidate axis per cluster, N sets per run" the right rule, or should the number of sets follow the number of clusters?
- Backcasting searches for evidence of each scenario, which invites confirmation bias. The step asks for signals against it too (20 of 71 in the first run); is that enough?
- The rubric grader runs on the same model as the agent and passes most answers at the first check; consider a stronger grader.
