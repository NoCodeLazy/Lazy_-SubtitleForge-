# 第三方许可声明 (Third-Party Notices)

本项目基于 **GPL-3.0** 协议开源，详见根目录 `LICENSE`。

以下为本项目使用的主要第三方组件及其许可证。部分许可证文本随项目分发，详见 `SubtitleAgent/bin/ffmpeg-licenses/`。

## Copyleft 组件（影响本项目整体许可证）

| 组件 | 用途 | 许可证 | 许可证文本位置 |
| --- | --- | --- | --- |
| pysrt | 字幕解析与 SRT 生成 | GPL-3.0 | 随 pip 包分发（见 `pysrt` 安装目录） |
| FFmpeg（`SubtitleAgent/bin/` 内置二进制，版本 `n7.1.5-12-g1fdbca85aa-20260806`） | 字幕烧录进视频 | GPL-2.0-or-later（包含 GPL-3.0 / LGPL-3.0 组件，构建参数含 `--enable-gpl --enable-version3`） | `SubtitleAgent/bin/ffmpeg-licenses/` |

### FFmpeg 说明

内置 ffmpeg 二进制由 `--enable-gpl --enable-version3` 构建，包含 libx264、libx265、libxvid 等 GPL 组件，整体按 GPL-2.0-or-later 授权。本项目的 `FFmpegUtil.py` 通过独立的 `ffmpeg` 子进程调用该二进制，未与其链接。

- 对应源码：FFmpeg 官方源码仓库（版本 `n7.1.5-12-g1fdbca85aa-20260806`，构建配置见 `ffmpeg -version` 输出）
- 源码获取地址：<https://ffmpeg.org/download.html> 或 <https://github.com/FFmpeg/FFmpeg>
- 许可证文本：`SubtitleAgent/bin/ffmpeg-licenses/` 目录下的 `LICENSE.md`、`COPYING.GPLv2`、`COPYING.GPLv3`、`COPYING.LGPLv2.1`、`COPYING.LGPLv3`

## 宽松许可证组件（无 Copyleft 义务）

| 组件 | 用途 | 许可证 |
| --- | --- | --- |
| fastapi | Web 框架 | MIT |
| uvicorn | ASGI 服务器 | BSD-3-Clause |
| python-multipart | 文件上传解析 | Apache-2.0（部分 MIT） |
| whisperx | 语音识别与字级对齐 | BSD-2-Clause |
| langchain / langchain-core / langchain-openai | LLM 调用 | MIT |
| ffmpeg-python | ffmpeg 命令封装 | Apache-2.0 |

## 运行时下载的模型

以下模型**不随本项目仓库分发**，由使用者在首次使用前自行从 Hugging Face 下载到本地模型目录（本项目默认开启离线模式，不会自动联网下载）。请遵守各模型自身的许可证。

| 模型 | 用途 | 许可证 |
| --- | --- | --- |
| [Systran/faster-whisper-large-v3](https://huggingface.co/Systran/faster-whisper-large-v3)（CTranslate2 格式，对应 OpenAI Whisper large-v3） | 语音转写 | MIT |
| [jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn](https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn) | 字级时间对齐 | Apache-2.0 |

对齐模型引用：

```bibtex
@misc{grosman2021xlsr53-large-chinese,
  title={Fine-tuned {XLSR}-53 large model for speech recognition in {C}hinese},
  author={Grosman, Jonatas},
  howpublished={\url{https://huggingface.co/jonatasgrosman/wav2vec2-large-xlsr-53-chinese-zh-cn}},
  year={2021}
}
```