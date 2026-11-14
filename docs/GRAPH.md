# The graphs

Digital Futures has one scenario graph, compiled once and used for every run. Some of its steps
build a second, smaller graph of their own each time they run: an agent. Most steps do not.

The drawings on this page, except the first, are generated from the nodes and edges of the
compiled graphs (LangGraph's `get_graph()`). They are written in plain Mermaid so that they
render in any Markdown preview. To draw them again after a change:

```bash
uv run python scripts/draw_graphs.py docs/graphs
```

## Overview

The eleven steps in order, coloured by what runs inside each one: grey for no AI, blue for a
tool agent, yellow for a deep agent graded against a rubric, green for direct model calls. A
person reviews the result of every step after the scope. This drawing is written by hand; the
ones below are generated.

```mermaid
flowchart TB
    subgraph scan["Scan"]
        direction LR
        scope["1 · scope"] --> drivers["2 · drivers"] --> clusters["3 · clusters"]
    end
    subgraph prioritise["Prioritise"]
        direction LR
        score_impact["4a · impact and uncertainty"] --> score_policy["4b · policy attention"] --> critical["5 · critical drivers"]
    end
    subgraph build["Build"]
        direction LR
        axes["6 · axes"] --> signals["6b · signals"] --> quadrants["7 · quadrants"]
    end
    subgraph tell["Tell"]
        direction LR
        narratives["8 · narratives"] --> backcast["9 · backcasting"]
    end
    scan --> prioritise --> build --> tell

    classDef plain fill:#eeeeee,stroke:#555555,color:#111111
    classDef tool fill:#cfe3ff,stroke:#2b5fa8,color:#111111
    classDef deep fill:#ffe08a,stroke:#9a6b00,color:#111111
    classDef calls fill:#d8f0d8,stroke:#2f7d32,color:#111111
    class scope plain
    class drivers tool
    class clusters,axes deep
    class score_impact,score_policy,critical,signals,quadrants,narratives,backcast calls
```

| Step | What runs inside | Its own graph |
| --- | --- | --- |
| 1 · scope | No AI: defaults or the form | None |
| 2 · drivers | A tool agent: the model calls web and paper search until it has enough | Simple: model and tools in a loop |
| 3 · clusters | A deep agent whose answer a grader checks against a rubric, up to three times | Complex: model, tools and the grader's checks |
| 4a · impact and uncertainty | One model call per cluster, in parallel | None |
| 4b · policy attention | One web search per driver in code, then one model call per cluster | None |
| 5 · critical drivers | One model call | None |
| 6 · axes | A deep agent graded against a rubric, as in step 3 | Complex: same shape as step 3 |
| 6b · signals | Searches per pole and per axis in code, then one model call per axis | None |
| 7 · quadrants | One model call per matrix | None |
| 8 · narratives | One model call per scenario | None |
| 9 · backcasting | Two model calls per scenario, with searches in code between them | None |

## The scenario graph

Every step is followed by a review node. The review pauses the run and waits for a person, who
approves the result, edits it, or sends it back with feedback. The dotted arrows are that
choice: back to the same step, or on to the next. Steps keep the colours of the overview and
review nodes are pink. With review switched off (`hitl=False`) the
review nodes approve on their own and the graph runs straight through.

```mermaid
flowchart TB
    n0["start"]
    n1["scope"]
    n2["drivers"]
    n3["review_drivers"]
    n4["clusters"]
    n5["review_clusters"]
    n6["score_impact"]
    n7["review_score_impact"]
    n8["score_policy"]
    n9["review_score_policy"]
    n10["critical"]
    n11["review_critical"]
    n12["axes"]
    n13["review_axes"]
    n14["signals"]
    n15["review_signals"]
    n16["quadrants"]
    n17["review_quadrants"]
    n18["narratives"]
    n19["review_narratives"]
    n20["backcast"]
    n21["review_backcast"]
    n22["end"]
    n0 --> n1
    n12 --> n13
    n20 --> n21
    n4 --> n5
    n10 --> n11
    n2 --> n3
    n18 --> n19
    n16 --> n17
    n13 -.-> n12
    n13 -.-> n14
    n21 -.-> n22
    n21 -.-> n20
    n5 -.-> n4
    n5 -.-> n6
    n11 -.-> n12
    n11 -.-> n10
    n3 -.-> n4
    n3 -.-> n2
    n19 -.-> n20
    n19 -.-> n18
    n17 -.-> n18
    n17 -.-> n16
    n7 -.-> n6
    n7 -.-> n8
    n9 -.-> n10
    n9 -.-> n8
    n15 -.-> n16
    n15 -.-> n14
    n1 --> n2
    n6 --> n7
    n8 --> n9
    n14 --> n15
    classDef terminal fill:#ffffff,stroke:#555555,color:#111111
    classDef plain fill:#eeeeee,stroke:#555555,color:#111111
    classDef tool fill:#cfe3ff,stroke:#2b5fa8,color:#111111
    classDef review fill:#f6e3f3,stroke:#8a3d7c,color:#111111
    classDef deep fill:#ffe08a,stroke:#9a6b00,color:#111111
    classDef calls fill:#d8f0d8,stroke:#2f7d32,color:#111111
    class n0,n22 terminal
    class n1 plain
    class n2 tool
    class n3,n5,n7,n9,n11,n13,n15,n17,n19,n21 review
    class n4,n12 deep
    class n6,n8,n10,n14,n16,n18,n20 calls
```

## Inside step 2: the tool agent

The model decides which searches to run, reads the results and searches again until it can
answer. Its tools are Tavily web search and Asta paper search. Dotted arrows are choices the
agent makes at run time.

```mermaid
flowchart TB
    n0["start"]
    n1["model"]
    n2["tools: tavily_search, find_papers"]
    n3["end"]
    n0 --> n1
    n1 -.-> n3
    n1 -.-> n1
    n1 -.-> n2
    n2 -.-> n3
    n2 -.-> n1
    classDef terminal fill:#ffffff,stroke:#555555,color:#111111
    classDef plain fill:#eeeeee,stroke:#555555,color:#111111
    class n0,n3 terminal
    class n1,n2 plain
```

## Inside steps 3 and 6: the deep agent with a grader

Steps 3 and 6 build the same graph with different prompts and rubrics. After the model
answers, `RubricMiddleware.after_agent` has a second model grade the answer against the
rubric. If a criterion fails, the answer goes back to the model with the gaps named; after
three checks the last answer is kept.

The tools listed in the drawing (files, shell, sub-agents) are the ones every deep agent
carries by default. The prompts of both steps tell the agent to answer directly and not use
them.

```mermaid
flowchart TB
    n0["start"]
    n1["model"]
    n2["tools: ls, read_file, write_file, edit_file, delete, glob, grep, execute, task"]
    n3["_ParentNotifierMiddleware.after_agent"]
    n4["PatchToolCallsMiddleware.before_agent"]
    n5["RubricMiddleware.before_agent"]
    n6["RubricMiddleware.after_agent"]
    n7["end"]
    n4 --> n5
    n6 -.-> n3
    n6 -.-> n1
    n5 --> n1
    n0 --> n4
    n1 -.-> n6
    n1 -.-> n1
    n1 -.-> n2
    n2 -.-> n6
    n2 -.-> n1
    n3 --> n7
    classDef terminal fill:#ffffff,stroke:#555555,color:#111111
    classDef plain fill:#eeeeee,stroke:#555555,color:#111111
    class n0,n7 terminal
    class n1,n2,n3,n4,n5,n6 plain
```

## Why the inner graphs do not appear in the scenario graph

The agents are created and run inside the step's function. They are not registered as
subgraphs of the scenario graph, so LangGraph draws each step as a single node, and review,
saved results and the run record all work at the level of the step.
