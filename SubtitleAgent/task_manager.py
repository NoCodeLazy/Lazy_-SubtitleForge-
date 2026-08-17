import json
import os
import threading
import time
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
UPLOAD_DIR = os.path.join(OUTPUT_DIR, "_uploads")


class Job:
    def __init__(self, task_id, source_type, source_path, theme=""):
        self.task_id = task_id
        self.source_type = source_type  # upload | path
        self.source_path = source_path
        self.theme = theme or ""
        self.state = "pending"  # pending | running | done | error
        self.phase = 1
        self.step = "等待开始"
        self.progress = 0
        self.message = ""
        self.error = None
        self.work_dir = None
        self.subtitle_path = None
        self.output_video_path = None
        self.segments = []
        self.word_segments = []
        self.text_segments = []
        self.text_after_llm = []
        self.corrections_report = []
        self.result = {}
        self.created_at = time.time()
        self.updated_at = time.time()

    def set_state(self, state, step=None, progress=None, message=None, error=None):
        self.state = state
        if step is not None:
            self.step = step
        if progress is not None:
            self.progress = progress
        if message is not None:
            self.message = message
        if error is not None:
            self.error = error
        self.updated_at = time.time()

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "source_type": self.source_type,
            "source_path": self.source_path,
            "theme": self.theme,
            "state": self.state,
            "phase": self.phase,
            "step": self.step,
            "progress": self.progress,
            "message": self.message,
            "error": self.error,
            "segments": self.segments,
            "word_segments": self.word_segments,
            "text_segments": self.text_segments,
            "text_after_llm": self.text_after_llm,
            "corrections_report": self.corrections_report,
            "result": self.result,
            "work_dir": self.work_dir,
            "subtitle_path": self.subtitle_path,
            "output_video_path": self.output_video_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, d):
        job = cls(d["task_id"], d.get("source_type", "path"), d.get("source_path", ""), d.get("theme", ""))
        job.state = d.get("state", "pending")
        job.phase = d.get("phase", 1)
        job.step = d.get("step", "")
        job.progress = d.get("progress", 0)
        job.message = d.get("message", "")
        job.error = d.get("error")
        job.work_dir = d.get("work_dir")
        job.subtitle_path = d.get("subtitle_path")
        job.output_video_path = d.get("output_video_path")
        job.segments = d.get("segments", [])
        job.word_segments = d.get("word_segments", [])
        job.text_segments = d.get("text_segments", [])
        job.text_after_llm = d.get("text_after_llm", [])
        job.corrections_report = d.get("corrections_report", [])
        job.result = d.get("result", {})
        job.created_at = d.get("created_at", time.time())
        job.updated_at = d.get("updated_at", time.time())
        return job


class TaskManager:
    def __init__(self):
        self._jobs = {}
        self._lock = threading.Lock()
        self.active_task_id = None

    def load_from_disk(self):
        if not os.path.isdir(OUTPUT_DIR):
            return
        for name in os.listdir(OUTPUT_DIR):
            task_json = os.path.join(OUTPUT_DIR, name, "task.json")
            if not os.path.isfile(task_json):
                continue
            try:
                with open(task_json, "r", encoding="utf-8") as f:
                    d = json.load(f)
                job = Job.from_dict(d)
                if job.state == "done":
                    self._jobs[job.task_id] = job
            except Exception:
                pass

    def create(self, source_type, source_path, theme=""):
        task_id = uuid.uuid4().hex[:12]
        job = Job(task_id, source_type, source_path, theme)
        self._jobs[task_id] = job
        return job

    def get(self, task_id):
        return self._jobs.get(task_id)

    def list(self):
        jobs = sorted(self._jobs.values(), key=lambda x: x.created_at, reverse=True)
        return [j.to_dict() for j in jobs]

    def clear_all(self):
        with self._lock:
            self._jobs.clear()
            self.active_task_id = None

    def acquire_active(self, job):
        with self._lock:
            if self.active_task_id is not None and self.active_task_id != job.task_id:
                return False
            self.active_task_id = job.task_id
            return True

    def release_active(self, job):
        with self._lock:
            if self.active_task_id == job.task_id:
                self.active_task_id = None

    def save(self, job):
        if not job.work_dir:
            return
        os.makedirs(job.work_dir, exist_ok=True)
        with open(os.path.join(job.work_dir, "task.json"), "w", encoding="utf-8") as f:
            json.dump(job.to_dict(), f, ensure_ascii=False, indent=2)


task_manager = TaskManager()
