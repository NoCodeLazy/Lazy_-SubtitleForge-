import pysrt
import re


def removeOthers(text: str) -> list:

    result = [s for s in re.split(r'[，。？]', text) if s.strip()]

    # 去除符号的result
    resultWithOutPoint = []

    for s in result:
        s = re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', s)
        resultWithOutPoint.append(s)

    return resultWithOutPoint


def build_segments(word_segments: list, text: list, textAfterLLM: list) -> list:
    """根据字级时间戳与分段文本，构建带序号的字幕分段列表"""
    segments = []
    wordi = 0
    for i, seg in enumerate(text):
        l = len(seg)
        if l <= 0:
            continue
        if wordi + l - 1 >= len(word_segments):
            break
        segments.append({
            "seq": i,
            "start": round(word_segments[wordi]['start'], 3),
            "end": round(word_segments[wordi + l - 1]['end'], 3),
            "text": textAfterLLM[i]
        })
        wordi += l
    return segments


def replace_word(text: str, old_word: str, new_word: str):
    """在文本中替换第一次出现的旧词，返回 (新文本, 是否成功)"""
    idx = text.find(old_word)
    if idx == -1:
        return text, False
    return text[:idx] + new_word + text[idx + len(old_word):], True


def export_srt(output_path: str, word_segments: list, text: list, textAfterLLM: list) -> str:
    """生成字幕文件"""
    print(f"📝 生成字幕: {output_path}")
    subs = pysrt.SubRipFile()

    segments = build_segments(word_segments, text, textAfterLLM)
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
