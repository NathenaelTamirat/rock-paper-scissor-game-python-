# Rock Paper Scissors Game

[![CI](https://github.com/NathenaelTamirat/rock-paper-scissor-game-python-/actions/workflows/ci.yml/badge.svg)](https://github.com/NathenaelTamirat/rock-paper-scissor-game-python-/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/NathenaelTamirat/rock-paper-scissor-game-python-/actions/workflows/pages.yml/badge.svg)](https://github.com/NathenaelTamirat/rock-paper-scissor-game-python-/actions/workflows/pages.yml)

A Python-based Rock Paper Scissors game with FastAPI backend, JavaScript frontend, adaptive memory AI, multiplayer support, and tournament mode.

## Project Structure

```
app/          - Python backend (FastAPI)
static/       - Frontend (HTML/CSS/JS)
tests/        - Pytest test suite
.github/      - GitHub Actions (CI + Pages)
```

## Deployment

### Backend

Run locally:

```
python -m app.main
```

The server starts at `http://localhost:8000`. Open the browser to play.

### Frontend (GitHub Pages)

The `static/` directory auto-deploys to GitHub Pages on every push to `main`.
To use Pages with a remote backend, edit `static/config.js` and set `API_BASE_URL` to your backend URL.

**To enable Pages:**
1. Go to repo Settings → Pages
2. Source: **GitHub Actions** (the workflow is already in `.github/workflows/pages.yml`)
