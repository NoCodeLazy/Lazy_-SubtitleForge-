import os
import shutil
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from SubtitleAgent.config_manager import config_manager
from SubtitleAgent.task_manager import task_manager, OUTPUT_DIR, UPLOAD_DIR
from SubtitleAgent.pipeline import pipeline

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
task_manager.load_from_disk()

app = FastAPI(title="Subtitle Agent", description="本地视频字幕生成与修正工具")


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/tasks")
def list_tasks():
    return {"tasks": task_manager.list()}


@app.post("/api/process")
def process(
        file: UploadFile = File(None),
        video_path: str = Form(""),
        theme: str = Form(""),
):
    if file is None and not video_path.strip():
        raise HTTPException(400, "请上传视频文件或填写本地视频路径")

    job = task_manager.create("upload" if file else "path", None, theme)

    if file:
        ext = os.path.splitext(file.filename or "")[1] or ".mp4"
        dest = os.path.join(UPLOAD_DIR, f"{job.task_id}{ext}")
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        job.source_path = dest
    else:
        job.source_path = video_path.strip()

    if not job.source_path or not os.path.isfile(job.source_path):
        raise HTTPException(400, f"视频文件不存在: {job.source_path}")

    if task_manager.active_task_id is not None:
        raise HTTPException(409, "已有任务正在处理，请等待完成后再试")

    pipeline.start_phase1_async(job)
    return {"task_id": job.task_id}


@app.get("/api/task/{task_id}")
def task_status(task_id: str):
    job = task_manager.get(task_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    return job.to_dict()


@app.post("/api/task/{task_id}/apply")
def apply_corrections(task_id: str, req: dict):
    job = task_manager.get(task_id)
    if not job:
        raise HTTPException(404, "任务不存在")
    corrections = (req or {}).get("corrections", [])
    if task_manager.active_task_id is not None:
        raise HTTPException(409, "已有任务正在处理，请等待完成后再试")
    pipeline.start_phase2_async(job, corrections)
    return {"task_id": job.task_id}


@app.get("/media/{task_id}/subtitle")
def subtitle_file(task_id: str):
    job = task_manager.get(task_id)
    if not job or not job.subtitle_path or not os.path.isfile(job.subtitle_path):
        raise HTTPException(404, "字幕文件不存在")
    return FileResponse(
        job.subtitle_path,
        media_type="application/x-subrip",
        filename=os.path.basename(job.subtitle_path),
    )


@app.get("/media/{task_id}/video")
def video_file(task_id: str, download: bool = False):
    job = task_manager.get(task_id)
    if not job or not job.output_video_path or not os.path.isfile(job.output_video_path):
        raise HTTPException(404, "视频文件不存在")
    if download:
        return FileResponse(
            job.output_video_path,
            media_type="video/mp4",
            filename=os.path.basename(job.output_video_path),
        )
    return FileResponse(job.output_video_path, media_type="video/mp4")


@app.post("/api/tasks/clear")
def clear_all_tasks():
    if task_manager.active_task_id is not None:
        raise HTTPException(409, "有任务正在处理，请等待完成后再清理")
    task_manager.clear_all()
    if os.path.isdir(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return {"ok": True, "message": "已清空所有上传视频和处理结果"}


@app.get("/api/settings")
def get_settings():
    return config_manager.to_dict()


@app.put("/api/settings")
def put_settings(req: dict):
    config_manager.update(req or {})
    return config_manager.to_dict()


@app.post("/api/settings/reload-model")
def reload_model():
    if task_manager.active_task_id is not None:
        raise HTTPException(409, "有任务正在运行，暂不能重新加载模型")
    try:
        pipeline.reload_model()
        return {"ok": True, "message": "模型重新加载完成"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "message": str(e)})
