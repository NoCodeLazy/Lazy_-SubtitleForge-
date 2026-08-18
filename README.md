# Subtitle Agent

一个简单易用的视频字幕生成工具。可基于本地faster-Whisper 进行语音识别并用Wav2Vec2进行字级时间对齐，再结合大语言模型（LLM）对字幕内容进行智能修正，再经过逻辑处理，最后通过 ffmpeg 将字幕烧录进视频画面。LLM调用是OpenAI规范，你可以选默认的ds，或本地部署，当前程序逻辑对本地小模型较为友好。算力有限，本地仅测试过4B小模型，效果尚可。



## 功能特性

- **语音识别**：使用 WhisperX（faster-whisper）进行音频转写，并用Wav2Vec2字级时间对齐，保证字幕时间轴精准
- **LLM 智能修正**：逐段调用 LLM（默认 DeepSeek）修正识别错误，可结合视频主题提升准确率，并自动补齐标点
- **两阶段处理流程**：
  - 阶段一：语音转写 → 字级对齐 →合并部分分段→ LLM 修正→将LLM优化结果分段，结合之前的字级时间戳和“段级时间约束”确认llm分段结果的时间戳→ 生成 SRT 字幕预览
  - 阶段二：在页面确认/修改字词 → 重新生成字幕 → 烧录进视频
- **本地 Web 界面**：浏览器操作，支持上传视频或填写本地路径
- **任务管理**：单任务串行处理，已完成任务持久化到磁盘，重启后仍可访问
- **离线支持**：默认离线模式使用本地 Hugging Face 模型缓存，请自行下载，详见后文
- **自带 ffmpeg**：`bin/` 目录内置 ffmpeg 二进制，无需额外安装

## 可用性测试

- **测试环境**：CPU:i7-12650H GPU:4060laptop 
- **测试时设置**：启用cuda（加快语音转文字以及字级对齐速度），分段最大秒数设置为30s，模型调用选择deepseek v4 flash，其他为默认设置
- **测试项目**：一段7分36秒的探店视频的字幕生成


- **总时间以及各步骤耗时**：
- 消耗总时间：约3分20秒
- 转录模型及对齐模型加载时间（每次程序重新启动后，第一次处理视频才会进行该步骤）:22s
- 转录以及对齐时间：共1分钟
- LLM修正优化耗时：36秒
- 烧录耗时约：1分20秒


- **成本**：非高峰时段进行的测试，约2分钱

- **效果**：字幕正确率高，且与声音较为同步，解决了本项目之前长视频易出现字幕与声音不同步的问题。暂未在更长视频上测试，但逻辑上来讲，当前处理下是误差基本是不会跨段累积的。



## 技术栈

| 模块 | 技术 |
| --- | --- |
| Web 框架 | FastAPI + Uvicorn |
| 语音识别 | WhisperX（whisperx） |
| 字幕处理 | pysrt |
| LLM 调用 | langchain + langchain-openai |
| 视频处理 | ffmpeg（`bin/` 内置） |

## 环境要求

- Python 3.9+
- NVIDIA GPU 与 CUDA（此为可选项，语音识别默认使用 `cuda`，若改为 `cpu`，则无需gpu和cuda）
- 关于语音模型部分请见下文

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 config.json（关键：填入 llm.api_key，也可在项目启动后进入设置页面设置并保存）
#    SubtitleAgent/config.json

# 3. 启动服务
python run.py
```

正常情况下启动后会自动打开浏览器，访问 `http://127.0.0.1:8080`。

初次使用请在页面自动打开后，点击右上角设置选项，设置好llm调用相关选项，以及按需设置whisper部分的分段最大秒数这一选项，默认为90s，如果追求效果请调为30s。其他选项最好先保持默认，然后点击“保存”后生效。或者你也可以去修改config.json



## 模型准备（手动下载）

本项目默认开启 `whisper.offline: true`，**不会联网自动下载模型**。若本地没有模型，运行时会提示模型缺失，因此首次使用前需手动下载以下两个模型：

| 模型 | 用途 | 许可证 |
| --- | --- | --- |
| [`Systran/faster-whisper-large-v3`](https://huggingface.co/Systran/faster-whisper-large-v3)（CTranslate2 格式，对应 Whisper large-v3） | 语音转写 | MIT |
| [`jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn`](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn) | 字级时间对齐 | Apache-2.0 |

下载方式（任选其一）：

```bash
# 方式一：使用 huggingface_hub 命令行下载（默认缓存布局，国内可加镜像前缀）
pip install -U huggingface_hub
hf download Systran/faster-whisper-large-v3
hf download jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn

# 国内用户可先设置镜像再执行上面的命令
$env:HF_ENDPOINT = "https://hf-mirror.com"

# 方式二：在浏览器中访问模型页，手动下载仓库文件（config.json / model.bin 等），
# 并按 HF hub 缓存结构放入模型目录，例如：
#   <cache_dir>\models--Systran--faster-whisper-large-v3\
#   <cache_dir>\models--jonatasgrosman--wav2vec2-large-xlsr-53-chinese-zh-cn\
```

下载完成后，在 `config.json` 中指定模型目录：

```json
{
  "whisper": {
    "cache_dir": "你的模型缓存目录（留空则使用系统默认 ~/.cache/huggingface/hub）",
    "offline": true
  }
}
```

修改配置后，可在界面「设置」中重新加载模型，或调用 `POST /api/settings/reload-model`。

## 使用流程

1. 在主页上传视频文件，或填写服务器本地视频路径（可附带视频主题）
2. 等待阶段一完成：语音转写 → 字级对齐 → LLM 修正 → 生成字幕预览
3. 在页面中浏览字幕，若个别字词识别错误，可提交修改（旧词 → 新词）
4. 确认无误后点击烧录，阶段二将修正后的字幕重新生成并烧录进视频
5. 完成后下载带字幕的视频或 SRT 字幕文件
6. 下载好后可点击右上的结束按钮，清除本地多余缓存，防止文件堆积。

## 配置说明

配置文件位于 `SubtitleAgent/config.json`，均可在前端设置页面进行修改（点击保存后，在下次任务生效）主要配置项如下：

### `llm` — 字幕修正大模型
| 键 | 说明 |
| --- | --- |
| `base_url` | OpenAI 兼容接口地址 |
| `api_key` | API 密钥 |
| `model_name` | 模型名称 |
| `enabled` | 是否启用 LLM 修正 |

### `whisper` — 语音识别
| 键 | 说明 |
| --- | --- |
| `model_size` | Whisper 模型大小（如 `large-v3`） |
| `device` | 运行设备（`cuda` / `cpu`） |
| `compute_type` | 计算精度（如 `int8`、`float16`） |
| `offline` | 是否启用离线模式 |
| `cache_dir` | Hugging Face 模型缓存目录；**留空则使用系统默认缓存**（`~/.cache/huggingface/hub`） |
| `language` | 识别语言（默认 `zh`） |
| `max_segment_duration` | 单段最大时长（秒），超过将分段 |

### `prompt` — LLM 提示词
- `system_template`：系统提示词模板，`{theme}` 会被替换为视频主题信息
- `theme_prefix`：主题信息前缀

### `ffmpeg` — 烧录参数
- `preset`、`crf`、`vcodec`、`pix_fmt`

### `subtitle_style` — 字幕样式
- `font_name`、`font_size`、`primary_color`、`outline_color`、`margin_v`、`outline`、`shadow`

### `server` — 服务配置
- `host`、`port`、`auto_open_browser`

## API 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/` | 前端页面 |
| GET | `/api/tasks` | 任务列表 |
| POST | `/api/process` | 创建任务并开始阶段一（上传文件或填写 `video_path`） |
| GET | `/api/task/{task_id}` | 查询任务状态与结果 |
| POST | `/api/task/{task_id}/apply` | 提交字词修正并开始阶段二烧录 |
| GET | `/media/{task_id}/subtitle` | 下载 SRT 字幕文件 |
| GET | `/media/{task_id}/video` | 预览/下载烧录后的视频 |
| POST | `/api/tasks/clear` | 清空所有任务及输出文件 |
| GET | `/api/settings` | 读取配置 |
| PUT | `/api/settings` | 更新配置 |
| POST | `/api/settings/reload-model` | 重新加载语音识别模型 |

## 项目结构

```
SubtitleAgent/
├── run.py                     # 启动入口
├── requirements.txt
└── SubtitleAgent/
    ├── app.py                 # FastAPI 接口定义
    ├── __main__.py            # uvicorn 启动逻辑
    ├── pipeline.py            # 两阶段处理流程（分析 / 烧录）
    ├── WhisperDemo.py         # WhisperX 语音识别与对齐封装
    ├── SrtUtil.py             # 字幕分段构建、字词替换、SRT 导出
    ├── FFmpegUtil.py          # ffmpeg 字幕烧录
    ├── task_manager.py        # 任务管理与持久化
    ├── config_manager.py      # 配置读取与合并
    ├── config.json            # 运行配置
    ├── static/index.html      # 前端页面
    ├── bin/                   # 内置 ffmpeg 二进制及其许可证文件
    └── output/                # 输出目录（上传、字幕、烧录视频）
```

## 开源许可

本项目采用 [GPL-3.0](LICENSE) 协议开源。由于项目引入 [pysrt](https://github.com/byroot/pysrt)（GPL-3.0）等 Copyleft 组件，按 GPL 规则组合作品须以 GPL-3.0 兼容协议整体发布。

- **版权说明**：`LICENSE` 为 GPL-3.0 全文
- **第三方组件声明**：详见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

### 内置 ffmpeg 说明

`SubtitleAgent/bin/` 内附 ffmpeg 二进制（版本 `n7.1.5-12-g1fdbca85aa-20260806`），为 `--enable-gpl` 构建，整体按 GPL-2.0-or-later 授权（含 GPL-3.0 / LGPL-3.0 组件）。本项目通过独立子进程调用它，并未与其链接。

依据 GPL 要求，随二进制分发其许可证文本与源码指引：

- 许可证文本：`SubtitleAgent/bin/ffmpeg-licenses/`（`LICENSE.md`、`COPYING.GPLv2`、`COPYING.GPLv3`、`COPYING.LGPLv2.1`、`COPYING.LGPLv3`）
- 源码获取：<https://ffmpeg.org/download.html> 或 <https://github.com/FFmpeg/FFmpeg>

> 注意：`config.json` 等本地配置（含 LLM API Key）已被 `.gitignore` 排除，不会随公开发布；使用前请自行配置。

## 写在最后
  此为本人agent学习过程中的练习项目，本人主要开发语言是java，此前虽用python写过一些小的程序和课设，但对前端和fastapi并不熟悉。最近学习langchain过程中有了这个idea，原本想做个agent，但最后成品感觉有点跑偏。虽然没完全按原本想法实现，但目前测试效果还算不错，也就暂时不去画蛇添足了。本项目高度借助code agent完成，代码部分，本人仅介入了核心部分的faster-Whisper、Wav2Vec2、LLM三者之间的流程设计，以及三者的输出结果处理。核心代码初步验证后利用code agent快速搭建起前端和其他后端逻辑，并在过程中不断测试优化处理逻辑，解决了长视频易出现字幕与声音不同步的问题。同时优化了一些其他地方，提高了易用性。本人精力有限，本readme存在ai生成部分，主要是在开源许可和后端相关api部分，如果使用过程中遇到问题，请灵活运用你的agent。

