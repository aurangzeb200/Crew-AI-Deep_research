from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import uuid
import asyncio
import os

from my_first_crew.crew import CompetitorResearchCrew


BASE_DIR = Path(__file__).resolve().parent  # src/my_first_crew
PROJECT_ROOT = BASE_DIR.parent.parent       # my_first_crew
OUTPUT_DIR = PROJECT_ROOT / "output"
STATIC_DIR = BASE_DIR / "web"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)


class StartRequest(BaseModel):
    company: str


class JobStatus(BaseModel):
    job_id: str
    stage: str
    message: Optional[str] = None
    file: Optional[str] = None


app = FastAPI(title="Competitor AI Server")


# in-memory job tracking
JOB_STATUS: dict[str, JobStatus] = {}


def set_status(job_id: str, stage: str, message: Optional[str] = None, file: Optional[str] = None):
    JOB_STATUS[job_id] = JobStatus(job_id=job_id, stage=stage, message=message, file=file)


async def run_pipeline(job_id: str, company: str):
    try:
        set_status(job_id, "exploring", f"Exploring sources for {company}…")

        inputs = {"company": company}

        # The crew orchestrates crawl -> news -> summarize sequentially
        set_status(job_id, "researching", f"Researching {company} across the web…")
        result = CompetitorResearchCrew().crew().kickoff(inputs=inputs)

        set_status(job_id, "analyzing", f"Analyzing findings for {company}…")

        # Output file path as per crew configuration
        filename = f"{company}_analysis.md"
        file_path = OUTPUT_DIR / filename
        if not file_path.exists():
            # Some CrewAI versions may write relative to CWD; search for the file in repo
            alt = Path.cwd() / "output" / filename
            if alt.exists():
                file_path = alt

        if file_path.exists():
            set_status(job_id, "done", "Completed", file=str(file_path.name))
        else:
            # Fall back to returning the text result as a file
            fallback = OUTPUT_DIR / filename
            fallback.write_text(str(result) if result is not None else "No result", encoding="utf-8")
            set_status(job_id, "done", "Completed", file=str(fallback.name))

    except Exception as exc:
        set_status(job_id, "error", f"{type(exc).__name__}: {exc}")


@app.post("/api/start", response_model=JobStatus)
async def start_job(req: StartRequest):
    company = req.company.strip()
    if not company:
        raise HTTPException(status_code=400, detail="company is required")

    job_id = uuid.uuid4().hex
    set_status(job_id, "queued", f"Queued for {company}")
    asyncio.create_task(run_pipeline(job_id, company))
    return JOB_STATUS[job_id]


@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_status(job_id: str):
    status = JOB_STATUS.get(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="job not found")
    return status


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return FileResponse(file_path, media_type="text/markdown", filename=filename)


@app.get("/api/output/{filename}")
async def view_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="file not found")
    return PlainTextResponse(file_path.read_text(encoding="utf-8"))


app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")


def main():
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("my_first_crew.server:app", host="0.0.0.0", port=port, reload=False)


