# NGIML - Interface

FastAPI web interface for running NGIML inference from local checkpoints.

## Quick start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Put one or more `.pt` checkpoints inside `checkpoints/`.

3. Start the web app:

```bash
uvicorn app:app --reload
```

4. Open `http://127.0.0.1:8000`

## What the web UI does

- Auto-discovers every `.pt` file inside `checkpoints/`
- Lets the user choose a checkpoint from a dropdown
- Lets the user upload an image
- Runs inference using the existing runtime in `src/`
- Shows the input image, probability map, binary mask, and overlay
- Saves each run under `web_runs/<timestamp>-<image>-<id>/outputs/`

## Developer notes

- Main FastAPI entrypoint: `app.py`
- HTML template: `templates/index.html`
- Styles: `static/styles.css`
- Result files are served from `web_runs/`
- Existing CLI inference via `predict.py` still works
