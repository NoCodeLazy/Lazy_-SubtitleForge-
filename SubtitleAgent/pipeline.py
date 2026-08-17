import os
import re
import json
import threading
from . import SrtUtil, FFmpegUtil
from .config_manager import config_manager
from .task_manager import task_manager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")


def _json_default(o):
    if hasattr(o, "item"):
        return o.item()
    return str(o)


def _save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=_json_default)
        print(f"已保存分析文件: {path}")
    except Exception as e:
        print(f"保存分析文件失败: {path} - {e}")


def _save_text(path, text):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text or "")
        print(f"已保存分析文件: {path}")
    except Exception as e:
        print(f"保存分析文件失败: {path} - {e}")


class PipelineError(Exception):
    pass


class PipelineRunner:
    def __init__(self):
        self._generator = None
        self._model_lock = threading.Lock()

    # ---------- 模型 ----------

    def ensure_model(self):
        if self._generator is not None:
            return self._generator
        with self._model_lock:
            if self._generator is not None:
                return self._generator
            from .WhisperDemo import WhisperXSubtitleGenerator
            cfg = config_manager.get("whisper")
            self._generator = WhisperXSubtitleGenerator(
                cfg["model_size"],
                device=cfg["device"],
                compute_type=cfg["compute_type"],
                offline=cfg.get("offline", True),
                cache_dir=cfg.get("cache_dir", ""),
            )
            self._generator.load_models(language=cfg.get("language", "zh"))
            return self._generator

    def reload_model(self):
        with self._model_lock:
            self._generator = None
        self.ensure_model()
        return True

    # ---------- 第一阶段：分析（不烧录） ----------

    def run_phase1(self, job):
        try:
            if not task_manager.acquire_active(job):
                raise PipelineError("已有任务在运行，请等待完成")
            video_path = job.source_path

            job.set_state("running", step="初始化", progress=3)
            if not os.path.isfile(video_path):
                raise PipelineError(f"视频文件不存在: {video_path}")

            base_name = os.path.splitext(os.path.basename(video_path))[0]
            work_dir = os.path.join(OUTPUT_DIR, f"{base_name}_{job.task_id}")
            os.makedirs(work_dir, exist_ok=True)
            job.work_dir = work_dir
            job.subtitle_path = os.path.join(work_dir, f"{base_name}.srt")
            job.output_video_path = os.path.join(work_dir, f"{base_name}_sub.mp4")
            task_manager.save(job)

            job.set_state("running", step="加载语音识别模型中（首次较慢）", progress=8)
            gen = self.ensure_model()

            job.set_state("running", step="语音转写中", progress=15)
            whisper_segment = gen.transcribeVedio(audio_path=video_path)
            if len(whisper_segment) == 0:
                raise PipelineError("未能从视频中识别出任何语音内容")
            _save_json(os.path.join(work_dir, "whisper_transcript.json"), gen.transcribe)

            job.set_state("running", step="字级时间对齐中", progress=35)
            r = gen.alignTranscribe()
            raw_word_segments = r[0]
            _save_json(os.path.join(work_dir, "whisper_align.json"), raw_word_segments)
            word_segments = [{"start": w["start"], "end": w["end"]} for w in raw_word_segments]

            # LLM 逐段修正
            segment = r[1]
            all_text = ''
            total_chunks = max(len(segment), 1)
            for idx, s in enumerate(segment):
                job.set_state("running", step=f"LLM 字幕修正中 ({idx + 1}/{total_chunks})",
                              progress=round(50 + 30 * (idx + 1) / total_chunks))
                llm_text = self._llm_correct(s['text'], job.theme)
                s['text'] = llm_text
                all_text = all_text + '\n' + llm_text
            _save_text(os.path.join(work_dir, "llm_text.txt"), all_text)

            job.set_state("running", step="分段处理中", progress=85)
            remove_others_and_list = SrtUtil.removeOthersAndToList(segment)
            # 将各段文本按句拆分（保留符号），供显示使用
            for s in segment:
                s['text'] = [t for t in re.split(r'[，。？]', s['text']) if t.strip()]
            text_after_llm = segment

            job.set_state("running", step="生成字幕文件中", progress=90)
            job.segments = SrtUtil.build_segments(word_segments, remove_others_and_list, text_after_llm)
            job.word_segments = word_segments
            job.text_after_llm = [seg['text'] for seg in job.segments]
            SrtUtil.export_srt_from_segments(job.segments, job.subtitle_path)

            job.result = {
                "segments": job.segments,
                "subtitle_url": f"/media/{job.task_id}/subtitle",
            }
            job.phase = 1
            job.set_state("done", step="分析完成，请确认字幕", progress=100)
            task_manager.save(job)
        except Exception as e:
            job.set_state("error", step="失败", error=str(e))
            task_manager.save(job)
        finally:
            task_manager.release_active(job)

    # ---------- 第二阶段：应用修改并烧录 ----------

    def run_phase2(self, job, corrections):
        backup = None
        try:
            if not task_manager.acquire_active(job):
                raise PipelineError("已有任务在运行，请等待完成")
            if not job.subtitle_path or not os.path.isfile(job.subtitle_path):
                raise PipelineError("任务尚未完成第一阶段，请先运行分析")

            job.set_state("running", step="应用字词修改中", progress=15)
            backup = [seg.get("text") for seg in job.segments]
            report = []
            for c in corrections or []:
                seq = c.get("seq")
                old_word = c.get("old_word")
                new_word = c.get("new_word")
                if seq is None or old_word is None or new_word is None:
                    report.append({"seq": seq, "success": False, "message": "修改参数不完整"})
                    continue
                if seq < 0 or seq >= len(job.segments):
                    report.append({"seq": seq, "success": False, "message": f"分段序号 {seq} 不存在"})
                    continue
                new_text, ok = SrtUtil.replace_word(job.segments[seq]["text"], old_word, new_word)
                if ok:
                    job.segments[seq]["text"] = new_text
                    report.append({"seq": seq, "success": True, "message": f"已替换 {old_word} -> {new_word}"})
                else:
                    report.append({"seq": seq, "success": False, "message": f"分段 {seq} 中未找到：{old_word}"})
            job.corrections_report = report

            job.set_state("running", step="重新生成字幕文件中", progress=50)
            SrtUtil.export_srt_from_segments(job.segments, job.subtitle_path)
            task_manager.save(job)

            job.set_state("running", step="烧录字幕中（较耗时，请耐心等待）", progress=65)
            FFmpegUtil.embed_subtitle_from_config(
                job.source_path,
                job.subtitle_path,
                job.output_video_path,
                style=config_manager.get("subtitle_style"),
                ffmpeg_cfg=config_manager.get("ffmpeg"),
            )

            job.result = {
                "segments": job.segments,
                "subtitle_url": f"/media/{job.task_id}/subtitle",
                "video_url": f"/media/{job.task_id}/video",
                "corrections_report": report,
            }
            job.phase = 2
            job.set_state("done", step="烧录完成", progress=100)
            task_manager.save(job)
        except Exception as e:
            if backup is not None:
                for k, seg in enumerate(job.segments):
                    if k < len(backup):
                        seg["text"] = backup[k]
            job.set_state("error", step="失败", error=str(e))
            task_manager.save(job)
        finally:
            task_manager.release_active(job)

    # ---------- 工具 ----------

    def _llm_correct(self, text, theme):
        llm_cfg = config_manager.get("llm")
        if not llm_cfg.get("enabled", True):
            raise PipelineError("LLM 字幕修正未启用，请在设置中开启")
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI

            model = ChatOpenAI(
                base_url=llm_cfg["base_url"],
                api_key=llm_cfg["api_key"],
                model=llm_cfg["model_name"],
            )
            prompt_cfg = config_manager.get("prompt")
            system = prompt_cfg.get("system_template", "")
            if theme and theme.strip():
                theme_line = f"{prompt_cfg.get('theme_prefix', '')}{theme.strip()}"
                system = system.replace("{theme}", theme_line)
            else:
                system = system.replace("{theme}", "")


            template = ChatPromptTemplate.from_messages([
                ("system", system),
                ("human", "{text}")
            ])
            chain = template | model
            res = chain.invoke({"text": text})
            return res.content
        except Exception as e:
            raise PipelineError(f"LLM 调用失败: {e}")

    def start_phase1_async(self, job):
        threading.Thread(target=self.run_phase1, args=(job,), daemon=True).start()

    def start_phase2_async(self, job, corrections):
        threading.Thread(target=self.run_phase2, args=(job, corrections), daemon=True).start()


pipeline = PipelineRunner()
