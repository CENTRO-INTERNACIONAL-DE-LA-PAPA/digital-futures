# Digital Futures

1. Define thematic, geographic and temporal scope.
    theme: food, land and water 
    geography: south countries
    current_time: 2026
    future_time: 2065

2. Identify drivers of change.
    how: web search to identify signals of change, Asta find papers to get lastest papers on certain issues.
    approach: AI + human in the loop

3. Cluster drivers.
    approach: AI + human in the loop

4. Vote for uncertainty, impact, and consideration of driver in political arenas.
    how can I define something is uncertain? No data retrieved from AI?
    how can I say a driver can have a high plausible impact in the future?
    how can I say a driver have impact in political areas?

5. identify critical drivers (most uncertain, highest impact and least discussed).
    Based on the votes and retrived information form AI, identify the most critical drivers.

6. Ideation of axes of uncertainty.
    The axes cannot be plus/minus, more/less, greater/lesser, etc. These need to be coordinated between AI and human in the loop.

7. Prioritize scenarios.
    AI can develop the four quadrants instead of prioritizing some scenarios over others.

8. Develop scenario narratives.
   The narratives need to be developed as we were: farmers, community leaders, scientists, policy makers.

# Guides for AI

- each step must be a node.
- the stack will be langgraph and deepagents (from langgraph).
- the codebase must be open source.
- the codebase must be written in python and with a clean code approach (less is more).
- the codebase must be easy to understand and maintain.

- With respect to the nodes:
    - node 1: I think there is no need for an llm in this node because we can fill manually or as default the state.
    - node 2: Here we need an llm (probably opus 5.5) with web search tool, asta find papers tool and interrupt in the flow so humans can provide feedback.
    - node 3: Probably the clustering need a deepagent (from langgraph) to cluster the drivers with grading rubrics.
    - node 4: Not sure about this, we need to planify it.
    - node 5: This is a node with an llm (probably opus 5.5).
    - node 6: This definitely needs a deepagent (from langgraph) with grading rubrics and human in the loop.
    - node 7: This is just a node with an llm (probably opus 5.5).
    - node 8: Becase these are narrative a gemini model will be enough.

# With respect to other specs:

- Quiero postgress como checkpointer y store para la memoria de los agentes (https://docs.langchain.com/oss/python/langgraph/add-memory).
- Langgraph interrupts: https://docs.langchain.com/oss/python/langgraph/interrupts 
- Deepagents: https://docs.langchain.com/oss/python/deepagents/quickstart
- Deepagents grading: https://docs.langchain.com/oss/python/deepagents/rubric
- Deepagents interrupts: https://docs.langchain.com/oss/python/deepagents/human-in-the-loop, https://docs.langchain.com/oss/python/deepagents/customization#human-in-the-loop

# History of work
- Marieke Veger ran this experiment: /home/ppalacios/Documents/digital_futures/historial_completo_FLW_2040.md
- These are previous findings: /home/ppalacios/Documents/digital_futures/Lessons learned_Probes to develop AI guided future scenarios_Marieke Veeger.docx
- This is the result of an in-person workshop: /home/ppalacios/Documents/digital_futures/workshop_results.qmd
- These are the last thooughts we got from Marieke: /home/ppalacios/Documents/digital_futures/last_email_from_marieke.txt

# Running

```bash
cp .env.example .env          # add API keys
docker compose up -d          # Postgres checkpointer + store
uv sync
(cd frontend && npm install && npm run build)   # build the web app once (needs Node 20+)
uv run digital-futures-web    # web app: http://localhost:8510 (React app + API)
uv run digital-futures        # terminal runner (new run); pass a run id to resume
uv run pytest
```

Development plan and design rules: [docs/PLAN.md](docs/PLAN.md).
