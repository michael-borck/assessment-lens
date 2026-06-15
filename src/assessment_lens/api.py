"""HTTP face of the lens — what a desktop shell (or any UI) talks to.

Assessment runs happen in a background worker thread; the UI polls progress. The
registry is in-memory and process-local: this server fronts one marker's desktop
app, not a multi-tenant service. Restarting the server forgets runs — the durable
record is whatever ``write_reports`` put on disk.

  POST /assessments              -> {id}            (starts a run)
  GET  /assessments              -> [{id, name, status, ...}]
  GET  /assessments/{id}         -> status + progress lines
  GET  /assessments/{id}/result  -> AssessmentResult (202 while running)
  GET  /health, GET /manifest    -> the family contract routes

Still a lens, not an analyser: it never scores. The result is observations a
human marks; this server just delivers them to a UI.
"""

from __future__ import annotations

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from lens_contract import add_contract_routes, add_cors
from pydantic import BaseModel, Field

from .assess import assess
from .manifest import MANIFEST
from .models import AssessmentResult
from .report import write_reports
from .rubric import load_rubric

app = FastAPI(title=MANIFEST["name"], version=MANIFEST["version"])
add_contract_routes(app, MANIFEST)
add_cors(app, env_prefix="ASSESSMENT_LENS")

# One cohort at a time: assessing shells out to the analyser stack per submission;
# a marker's desktop doesn't want two cohorts interleaving.
_executor = ThreadPoolExecutor(max_workers=1)


class _Run:
    def __init__(self, name: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.name = name
        self.status = "queued"  # queued | running | done | failed
        self.progress: list[str] = []
        self.result: AssessmentResult | None = None
        self.error: str = ""
        self.lock = threading.Lock()

    def say(self, msg: str) -> None:
        with self.lock:
            self.progress.append(msg)

    def summary(self) -> dict:
        with self.lock:
            return {
                "id": self.id,
                "name": self.name,
                "status": self.status,
                "progress": list(self.progress),
                "error": self.error,
            }


_runs: dict[str, _Run] = {}


class StartAssessment(BaseModel):
    """POST /assessments body: absolute paths to a rubric + a submissions folder.

    The server resolves nothing relative — the UI owns the filesystem dialogue and
    sends absolute paths. ``out`` is where the cohort sheet + reports land on disk
    (omit to skip writing). ``llm`` opts into narration (degrades to deterministic
    observations if no provider is configured). The lens never assigns marks.
    """

    rubric: Path
    submissions: Path
    out: Path | None = Field(default=None, description="Folder for sheet + reports; omit to skip.")
    only: list[str] | None = Field(default=None, description="Restrict to these submission ids.")
    llm: bool = False


def _execute(run: _Run, body: StartAssessment) -> None:
    run.status = "running"
    try:
        rubric = load_rubric(body.rubric)
        result = assess(rubric, body.submissions, only=body.only, llm=body.llm, progress=run.say)
        if body.out is not None:
            out = write_reports(result, body.out)
            run.say(f"wrote {out}/cohort-sheet.csv + per-student reports")
        with run.lock:
            run.result = result
            run.status = "done"
    except Exception as exc:
        with run.lock:
            run.error = str(exc)
            run.status = "failed"


@app.post("/assessments", status_code=202)
def start_assessment(body: StartAssessment) -> dict:
    run = _Run(body.rubric.stem)
    _runs[run.id] = run
    _executor.submit(_execute, run, body)
    return {"id": run.id}


@app.get("/assessments")
def list_assessments() -> list[dict]:
    return [run.summary() for run in _runs.values()]


@app.get("/assessments/{run_id}")
def get_assessment(run_id: str) -> dict:
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(404, f"no assessment {run_id}")
    return run.summary()


@app.get("/assessments/{run_id}/result")
def get_result(run_id: str):
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(404, f"no assessment {run_id}")
    with run.lock:
        if run.status == "failed":
            raise HTTPException(500, run.error)
        if run.result is None:
            return JSONResponse({"status": run.status}, status_code=202)
        return run.result.model_dump(mode="json")
