from __future__ import annotations

from datetime import datetime
from pathlib import Path
from uuid import uuid4
import shutil

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src import run_inference

BASE_DIR = Path(__file__).resolve().parent
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
WEB_RUNS_DIR = BASE_DIR / "web_runs"

app = FastAPI(title="NGIML Interface", version="1.0.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

STATIC_DIR.mkdir(parents=True, exist_ok=True)
WEB_RUNS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/results", StaticFiles(directory=str(WEB_RUNS_DIR)), name="results")


def list_checkpoints() -> list[dict[str, str]]:
    checkpoints: list[dict[str, str]] = []
    if not CHECKPOINTS_DIR.exists():
        return checkpoints

    for checkpoint_path in sorted(CHECKPOINTS_DIR.rglob("*.pt")):
        relative_path = checkpoint_path.relative_to(CHECKPOINTS_DIR).as_posix()
        checkpoints.append(
            {
                "value": relative_path,
                "label": relative_path,
            }
        )
    return checkpoints


def resolve_checkpoint(selection: str) -> Path | None:
    if not selection:
        return None
    checkpoint_path = (CHECKPOINTS_DIR / selection).resolve()
    try:
        checkpoint_path.relative_to(CHECKPOINTS_DIR.resolve())
    except ValueError:
        return None
    if checkpoint_path.is_file() and checkpoint_path.suffix == ".pt":
        return checkpoint_path
    return None


def build_run_dir(image_name: str) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_stem = Path(image_name).stem or "upload"
    safe_stem = "".join(ch for ch in safe_stem if ch.isalnum() or ch in {"-", "_"}) or "upload"
    return WEB_RUNS_DIR / f"{timestamp}-{safe_stem}-{uuid4().hex[:8]}"


def to_results_url(path: str | Path) -> str:
    relative = Path(path).resolve().relative_to(WEB_RUNS_DIR.resolve())
    return f"/results/{relative.as_posix()}"


def render_home(
    request: Request,
    *,
    selected_checkpoint: str | None = None,
    result: dict | None = None,
    error: str | None = None,
) -> HTMLResponse:
    checkpoints = list_checkpoints()
    if selected_checkpoint is None and checkpoints:
        selected_checkpoint = checkpoints[0]["value"]

    return templates.TemplateResponse(
        name="index.html",
        request=request,
        context={
            "checkpoints": checkpoints,
            "selected_checkpoint": selected_checkpoint,
            "result": result,
            "error": error,
        },
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return render_home(request)


@app.post("/predict", response_class=HTMLResponse)
async def predict(
    request: Request,
    checkpoint: str = Form(...),
    image: UploadFile = File(...),
) -> HTMLResponse:
    checkpoint_path = resolve_checkpoint(checkpoint)
    if checkpoint_path is None:
        return render_home(request, selected_checkpoint=checkpoint, error="Please choose a valid checkpoint.")

    if not image.filename:
        return render_home(request, selected_checkpoint=checkpoint, error="Please upload an image.")

    suffix = Path(image.filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}:
        return render_home(
            request,
            selected_checkpoint=checkpoint,
            error="Unsupported image type. Use PNG, JPG, JPEG, BMP, TIF, TIFF, or WEBP.",
        )

    run_dir = build_run_dir(image.filename)
    upload_dir = run_dir / "uploads"
    output_dir = run_dir / "outputs"
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    image_path = upload_dir / f"input{suffix}"
    with image_path.open("wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    try:
        prediction = run_inference(
            checkpoint_path=checkpoint_path,
            image_path=image_path,
            output_dir=output_dir,
        )
    except Exception as exc:
        return render_home(
            request,
            selected_checkpoint=checkpoint,
            error=f"Inference failed: {exc}",
        )
    finally:
        await image.close()

    saved_paths = prediction.get("saved_paths") or {}
    result = {
        "checkpoint": checkpoint_path.relative_to(CHECKPOINTS_DIR).as_posix(),
        "threshold": f"{prediction['threshold']:.4f}",
        "device": prediction["device"],
        "normalization_mode": prediction["normalization_mode"],
        "probability_mean": f"{float(prediction['probability'].mean().item()):.4f}",
        "probability_max": f"{float(prediction['probability'].max().item()):.4f}",
        "predicted_positive_ratio": f"{float(prediction['binary'].mean().item()):.4f}",
        "input_url": to_results_url(saved_paths["image_path"]),
        "probability_url": to_results_url(saved_paths["probability_path"]),
        "binary_url": to_results_url(saved_paths["binary_path"]),
        "overlay_url": to_results_url(saved_paths["overlay_path"]),
        "metadata_url": to_results_url(saved_paths["metadata_path"]),
        "output_dir": str(output_dir.resolve()),
    }
    return render_home(request, selected_checkpoint=checkpoint, result=result)
