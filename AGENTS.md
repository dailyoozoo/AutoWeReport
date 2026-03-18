# Repository Guidelines

## Project Structure & Module Organization
`src/` contains the Python application code. Use `src/web_server.py` for the FastAPI API and static file mount, `src/main_agent.py` for CLI report generation, `src/ai_planner/` for prompt, cleaning, and LLM logic, `src/formatters/` for merged chat export, and `src/extractors/` for WeChat extraction hooks. `web/` holds the static dashboard (`index.html`, `app.js`, `style.css`). Runtime data lives under `data/` and generated reports go to `workspace/reports/`. Treat `wechat-decrypt/` as an external helper area, not core app code.

## Build, Test, and Development Commands
This repo does not currently include `requirements.txt` or `pyproject.toml`, so install dependencies from the imported modules in the codebase before running locally.

```bash
python start_app.py
```
Starts the FastAPI server on `127.0.0.1:8080` and opens the dashboard.

```bash
python -m uvicorn src.web_server:app --host 127.0.0.1 --port 8080
```
Runs only the backend for API debugging.

```bash
python src/main_agent.py --daily
python src/main_agent.py --weekly
```
Generates reports from existing merged chat data.

## Coding Style & Naming Conventions
Use 4-space indentation in Python, JavaScript, HTML, and CSS. Follow existing Python naming: `snake_case` for functions and variables, `PascalCase` for classes, and `UPPER_CASE` for environment keys such as `NVIDIA_API_KEY`. Keep modules small and task-focused. In the frontend, prefer clear DOM ids that match backend config keys where practical.

## Testing Guidelines
There is no committed automated test suite yet. For new logic, add focused `pytest` tests under a new `tests/` directory and keep them close to pure functions such as data cleaning or formatting. Name files `test_<module>.py`. Before opening a PR, run the relevant CLI path and verify the web flow with `python start_app.py`.

## Commit & Pull Request Guidelines
The current history uses Conventional Commit style (`feat: init AutoWeReport MVP`); continue with prefixes like `feat:`, `fix:`, and `docs:`. Keep commits scoped to one change. PRs should include a short problem statement, implementation summary, manual verification steps, and screenshots for dashboard changes.

## Security & Configuration Tips
Do not commit `.env`, decrypted chat data, or generated reports. Keep machine-specific paths and API credentials in `.env`. If you touch path handling, avoid adding new hard-coded absolute Windows paths; prefer project-relative `Path` usage.
