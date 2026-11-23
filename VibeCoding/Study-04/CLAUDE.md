# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current state

`Study-04` has no source code yet: no build/lint/test tooling, no README. There is no architecture to document, so update this file once code exists (commands, entry points, how the pieces fit together).

Setup files for the OpenRouter-based project:

- `.env`: defines `OPENROUTER_API_KEY` (git-ignored by the root `.gitignore`). Never print or commit its value; load it from the environment. `.env.example` is the committed template (the root `.gitignore` un-ignores it).
- `모델.txt` (untracked): the chosen OpenRouter free-tier models, all NVIDIA. Image: `nvidia/nemotron-3.5-super-vl:free` (alt: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`), called via `/chat/completions` with a base64 `image_url`. Text: `nvidia/nemotron-3.5-lightning:free` via `/chat/completions`. It is a reasoning model: with a small `max_tokens` (e.g. 300) the reasoning eats the budget and `message.content` comes back `null`, so use several thousand (see below). Both were verified working on 2026-11-23. Dropped: `google/gemma-4-31b-it:free` (Google free pool kept returning 429) and `nvidia/nemotron-3.5-embed-8b:free` (embedding-only, can't generate text).

## Commands and architecture

Fridge-photo recipe app, built in 3 steps per `PRD_step1.md`..`PRD_step3.md` (Python + FastAPI, no login, single profile, bind `127.0.0.1` only). All three steps are implemented.

- Install: `pip install -r requirements.txt`
- Run: `python -m app.main` (http://127.0.0.1:8000). No test suite yet.
- `app/main.py`: app wiring plus step 1. `POST /api/recognize` validates/resizes the image (Pillow), asks the vision model for ingredients JSON, and returns `{ingredients:[{name,quantity,confidence}]}`.
- `app/recipes.py`: step 2. `POST /api/recipes` takes the confirmed ingredients plus conditions and returns 3 recipes (`title, summary, servings, time_minutes, difficulty, uses, missing, steps`). `parse_recipes` moves any `uses` item not in the input list into `missing` and drops recipes containing excluded ingredients.
- `app/saved.py` + `app/db.py`: step 3. Single profile (row id=1, no login) and saved recipes in SQLite at `data/app.db` (git-ignored; override with env `RECIPE_DB`, e.g. for tests). Endpoints: `GET/PUT /api/profile`, `GET/POST /api/saved`, `DELETE /api/saved/{id}`. Duplicates (same title + same ingredient set) return 409. Profile prefs (`exclude`, `servings`) prefill the step-2 form.
- `app/main.py` also has a middleware that rejects any request whose `Host` is not `127.0.0.1:8000`/`localhost:8000` and any state-changing request with a foreign `Origin`. This is the only protection since there is no login, so keep it and keep the server bound to `127.0.0.1`.
- `app/env.py`: loads `.env` once (`load_dotenv`); `app/db.py` and `app/openrouter.py` import it first, so `RECIPE_DB` in `.env` also works. The API key is still read only in `app/openrouter.py` (`api_key()`); never read env values elsewhere or print them.
- `app/openrouter.py`: shared OpenRouter call, backoff retry and model fallback (`run_with_fallback`: max 3 calls per model including parse/empty retries, 180 s overall deadline, honors 429 `Retry-After`, `finish_reason=length` retries at once), plus `extract_json_object` used by both parsers.
- `app/static/index.html`: single-page UI. The confirmed ingredient list is kept in `sessionStorage["ingredients"]`. Model output is always inserted with `textContent`.
- Models: vision `nemotron-3.5-super-vl:free` (fallback `nemotron-3-nano-omni-30b-a3b-reasoning:free`); text `nemotron-3.5-lightning:free` (fallback `nemotron-3-ultra-550b-a55b:free`).
- All of these are reasoning models: if `max_tokens` is too small the reasoning eats it and `content` comes back empty. Measured: vision needs about 4000 (1500 failed ~1 in 3), recipes need about 8000 (lightning used ~5800; 3000 always failed). A recipe call takes 30-60 s. An empty reply is retried once per model, then the next model is tried.
- `python -I` drops the cwd from `sys.path`; to import `app` in an ad-hoc script use `PYTHONPATH=.`.

## Repository context

`Study-04` sits in a git repo whose root is `C:\Users\User\Desktop\VibeCoding` (a `.gitignore` is at the root). Sibling directories `Study-01` to `Study-03` are independent study projects, each with its own `CLAUDE.md` and Korean `README.md`:

- `Study-01`: PyTorch MNIST handwriting digit recognition (`train.py`, `model.py`, `draw_and_predict.py`).
- `Study-02`: vanilla HTML/CSS/JS todo app, no build step.
- `Study-03`: vanilla JS quiz app with project slash commands in `.claude/commands/` (`quiz-add`, `quiz-range`, `quiz-validate`).

If Study-04 follows the same pattern, expect a self-contained project in this folder with a Korean README and a project-local `CLAUDE.md`, and commit it as its own `Add Study-04` style commit.
