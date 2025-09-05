# Repository Guidelines

## Project Structure & Module Organization
- Backend: `fyxerai_assistant/` (Django project) and `core/` (app: models, views, tasks, consumers, templates).
- Frontend assets: `static/` (`css/`, `js/`, `icons/`), Tailwind build outputs to `static/css/output.css`.
- Tests: `tests/` (pytest-based Python tests, Playwright e2e, Vitest unit/integration). Additional JS tests may exist at repo root.
- Tooling: `Dockerfile`, `docker-compose.yml`, `playwright.config.js`, `vitest.config.js`, `pytest.ini`, `scripts/` (maintenance utilities).

## Build, Test, and Development Commands
- Python setup: `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Run backend: `python manage.py migrate && python manage.py runserver`
- Frontend CSS (watch): `npm install && npm run dev`  • one-off build: `npm run build-css-once`  • prod: `npm run build-css-prod`
- JS tests (Vitest): `npm run test:run`  • watch: `npm test`  • coverage: `npm run test:coverage`
- E2E (Playwright): `npm run playwright:install` then `npm run test:e2e` (UI mode: `npm run test:e2e:ui`)
- Docker (optional): `docker-compose up --build`

## Coding Style & Naming Conventions
- Python: 4‑space indent; `snake_case` for functions/vars, `PascalCase` for classes. Run: `black . && isort . && flake8`.
- JavaScript: `camelCase` for functions/vars; keep modules small and cohesive; colocate component JS/CSS under `static/` when practical.
- Templates: keep reusable snippets in `core/templates/`; prefer semantic HTML with Tailwind utilities.

## Testing Guidelines
- Back end: `pytest` (Django configured via `pytest.ini`). Name tests `test_*.py` under `tests/`.
- Front end: Vitest for unit/integration (`tests/unit`, `tests/integration`); Playwright for e2e (`tests/e2e`). Aim for meaningful coverage (use `--coverage`).

## Commit & Pull Request Guidelines
- Commits: use Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `test:`, `chore:`). Keep to one logical change per commit.
- PRs: include summary, rationale, linked issues, and screenshots/GIFs for UI changes. Note env or migration impacts; update docs/tests accordingly.

## Security & Configuration
- Secrets: copy `.env.example` to `.env`; never commit secrets. Key settings live in `fyxerai_assistant/settings.py`.
- Local tips: ensure Redis and Postgres are available if using Celery/Channels; otherwise use Docker compose.
