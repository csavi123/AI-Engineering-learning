# LLM Learning Lab

A hands-on app for understanding how LLMs work. Every concept comes with an
experiment you run against Claude. You write a prediction first, then run the
experiment and compare.

- **Backend:** FastAPI (`backend/`). This is the only code that holds the API key and calls Anthropic.
- **Frontend:** Streamlit (`frontend/`). It has one sidebar page per section and talks to the backend over HTTP.
- **LLM:** Anthropic Claude through the official `anthropic` Python SDK.

## Setup

Use Python 3.9 or newer. 3.10+ is recommended because newer `anthropic` SDK releases need it.

```bash
cd AI_Conceptual_Understanding
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# open .env and paste your key: ANTHROPIC_API_KEY=sk-ant-...
```

## Run (two terminals, both with the venv activated)

```bash
# Terminal 1: backend
uvicorn backend.main:app --reload --port 8000

# Terminal 2: frontend
streamlit run frontend/app.py
```

Streamlit opens at http://localhost:8501. The backend's interactive API docs
are at http://localhost:8000/docs.

## Configuration (`config.yaml`)

| Setting | Meaning |
|---|---|
| `default_model` | Used by every experiment. Default: `claude-haiku-5-5`, the cheapest Claude model ($0.10 / $0.50 per M tokens). |
| `sampling_model` | Used where an experiment needs `temperature`/`top_p`/`top_k` or assistant prefill. Haiku 5.5 rejects all of these. Default: `claude-haiku-4-5` ($1 / $5 per M tokens). |
| `max_repeated_runs` | Hard cap on repeated calls in one experiment (30). |
| `models.<id>.*` | Prices per million tokens, context window, and which features the model supports. Edit the prices here. They are never hardcoded. |

Prices change, so check https://claude.com/pricing and update `config.yaml`
if they differ.

## Project layout

```
config.yaml              model names, prices, caps, monthly budget
.env                     ANTHROPIC_API_KEY (not committed)
content/
  syllabus.yaml          the 17 chapters (and which are built)
  ch01_how_llms_work.yaml  chapter 1: lesson text, diagrams, quizzes
backend/
  config.py              loads config.yaml + .env
  claude_client.py       call_claude() / stream_claude(): the shared helper
  spend.py               monthly spend tracking + budget guard
  main.py                FastAPI routes: /health, /config, /spend, /call, /stream, /count_tokens
frontend/
  app.py                 sidebar navigation (Home + built chapters)
  chapter.py             draws any chapter: overview, cheat sheet, lessons
  lesson_card.py         draws any lesson in the 6-part format
  quiz.py                multiple-choice quiz + scores
  demos/                 every demo, by id (free simulations and live demos)
  api.py, ui.py, charts.py, store.py   shared helpers
  views/home.py          the syllabus map
data/                    your saved runs, quiz progress, spend (not committed)
```

## How the app is organised

- **Home:** all 17 chapters. Built chapters link to their page.
- **Chapter page:** one picture + a 60-second cheat sheet, then one lesson at a time.
- **Lesson card:** the same 6 parts every time: core idea, picture, key points, one demo, quick quiz, and an optional "Go deeper".

### Keeping costs low
- 🆓 **Free demos** are local simulations: no API calls.
- 💲 **Live demos** call Claude only when you click Run. They show the estimated cost first, and the result is saved in `data/runs/`, so viewing it again later is free.
- **Spend guard:** the backend refuses calls once this month's estimated spend reaches `monthly_budget_usd` (default $1). The sidebar shows the running total.

### Adding a chapter
Write `content/chNN_*.yaml` in the same shape as chapter 1, point to it from `content/syllabus.yaml`, and add any new demos to `frontend/demos/`.

## Build status (chapter 1)

- ✅ Framework: syllabus map, chapter page, lesson cards, quizzes, saved runs, spend guard
- ✅ Lesson 01, written from the course text
- ✅ Lessons 02–07 and "Prove it": **drafts** written from general knowledge (marked 📝 in the app); paste each course lesson to align it
- ✅ "Quiz me" review page
