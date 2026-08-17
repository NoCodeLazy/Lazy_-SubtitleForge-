import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "llm": {
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "model_name": "deepseek-v4-flash",
        "enabled": True
    },
    "whisper": {
        "model_size": "large-v3",
        "device": "cuda",
        "compute_type": "int8",
        "offline": True,
        "cache_dir": "C:\\Users\\j2547\\.cache\\huggingface\\hub",
        "language": "zh",
        "max_segment_duration": 90
    },
    "prompt": {
        "system_template": "你是修正视频字幕的ai专家，结合视频主题修正字幕内容，并适当增添标点来分隔。你必须只输出最终结果，严禁输出任何解释、思考过程。{theme}",
        "theme_prefix": "本次视频主题为："
    },
    "ffmpeg": {
        "preset": "medium",
        "crf": 23,
        "vcodec": "libx264",
        "pix_fmt": "yuv420p"
    },
    "subtitle_style": {
        "font_name": "Microsoft YaHei",
        "font_size": 20,
        "primary_color": "&HFFFFFF",
        "outline_color": "&H80000000",
        "margin_v": 20,
        "outline": 2,
        "shadow": 1
    },
    "server": {
        "host": "127.0.0.1",
        "port": 8080,
        "auto_open_browser": True
    }
}


def _deep_merge(base, override):
    out = dict(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


class ConfigManager:
    def __init__(self, config_path=None):
        self.config_path = config_path or CONFIG_PATH
        self._config = {}
        self.load()

    def load(self):
        data = {}
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        self._config = _deep_merge(DEFAULT_CONFIG, data)
        self.save()

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)

    def get(self, *keys, default=None):
        node = self._config
        for k in keys:
            if isinstance(node, dict) and k in node:
                node = node[k]
            else:
                return default
        return node

    def to_dict(self):
        return self._config

    def update(self, patch):
        self._config = _deep_merge(self._config, patch)
        self.save()


config_manager = ConfigManager()
