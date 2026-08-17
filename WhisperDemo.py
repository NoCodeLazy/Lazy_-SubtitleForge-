import re

import pysrt
import whisperx
import os
# 获取当前脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))
ffmpeg_dll_path = os.path.join(script_dir, "bin")

# 转换为绝对路径并确保存在
ffmpeg_dll_path = os.path.abspath(ffmpeg_dll_path)

print(f"🔍 尝试加载DLL路径: {ffmpeg_dll_path}")

if os.path.exists(ffmpeg_dll_path):
    try:
        os.add_dll_directory(ffmpeg_dll_path)
        print(f"✅ 已添加DLL搜索路径: {ffmpeg_dll_path}")
    except Exception as e:
        print(f"❌ 添加DLL路径失败: {e}")
        # 尝试其他方法

class WhisperXSubtitleGenerator:
    """使用 WhisperX 生成更精准字幕"""

    def __init__(self, model_size, device, compute_type, offline=True, cache_dir=None):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.offline = offline
        self.cache_dir = cache_dir
        self._setup_environment(self.offline, self.cache_dir)
        self.model = None
        self.align_model = None
        self.align_metadata = None
        self.transcribe = None
        self.audio = None

    @staticmethod
    def _setup_environment(offline, cache_dir):
        """根据配置设置离线与缓存环境变量"""
        if offline:
            os.environ['HF_HUB_OFFLINE'] = '1'
            os.environ['TRANSFORMERS_OFFLINE'] = '1'
            os.environ['HF_DATASETS_OFFLINE'] = '1'
        else:
            os.environ.pop('HF_HUB_OFFLINE', None)
            os.environ.pop('TRANSFORMERS_OFFLINE', None)
            os.environ.pop('HF_DATASETS_OFFLINE', None)
        if cache_dir:
            os.environ['HF_HOME'] = cache_dir
            os.environ['HUGGINGFACE_HUB_CACHE'] = cache_dir
        print(f"📁 缓存目录: {cache_dir}")
        print(f"🔒 离线模式: {'已启用' if offline else '未启用'}")

    def load_models(self, language="zh"):
        """加载模型"""
        print(f"📦 加载 WhisperX 模型: {self.model_size}")
        self.model = whisperx.load_model(
            self.model_size,
            self.device,
            compute_type=self.compute_type,
        )

        # 加载对齐模型
        print(f"📦 加载对齐模型")
        self.align_model, self.align_metadata = whisperx.load_align_model(
            language_code=language,
            device=self.device
        )

    def transcribeVedio(self, audio_path, language="zh"):
        """转录"""
        print(f"🎤 开始转录: {audio_path}")

        # 1. 加载音频

        audio = whisperx.load_audio(audio_path)
        self.audio=audio
        # 2. 转录
        result = self.model.transcribe(audio, batch_size=16, language=language)
        self.transcribe=result



        #返回whisper结果
        allText = []
        for i in range(len(result["segments"])):
            texti: str = result["segments"][i]['text']
            texti = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', texti)
            result["segments"][i]['text']=texti
            allText.append(texti)

        result = "\n".join(allText)
        return result

    #对齐，获取词级时间戳
    def alignTranscribe(self)->list:

        transcribe=self.transcribe
        audio=self.audio
        result_aligned = whisperx.align(
            transcribe["segments"],
            self.align_model,
            self.align_metadata,
            audio,
            self.device,
            return_char_alignments=False
        )
        return result_aligned["word_segments"]


    def generate_srt(self, segments, output_path):
        """生成字幕文件"""
        print(f"📝 生成字幕: {output_path}")
        subs = pysrt.SubRipFile()



        for i, seg in enumerate(segments, start=1):
            start = pysrt.SubRipTime(seconds=seg['start'])
            end = pysrt.SubRipTime(seconds=seg['end'])
            item = pysrt.SubRipItem(
                index=i,
                start=start,
                end=end,
                text=seg['text']
            )
            subs.append(item)

        subs.save(output_path, encoding="utf-8")
        print(f"✅ 字幕文件保存成功")
        return output_path





if __name__=="__main__":
    generator = WhisperXSubtitleGenerator(
        "large-v3",
        device="cpu",
        compute_type="int8"
    )
    path= r"/SubtitleAgent\testVideo.mp4"
    generator.load_models()
    generator.transcribeVedio(audio_path=path)
