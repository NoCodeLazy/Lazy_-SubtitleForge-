import pysrt
import re


def removeOthersAndToList(segment) -> list:
    """将每段文本按句拆分并去除符号，返回 [{start, end, text:[子段...]}]"""
    out = []
    for seg in segment:
        text = seg['text']
        sub = [t for t in re.split(r'[，。？]', text) if t.strip()]
        stripped = [re.sub(r'[^a-zA-Z0-9\u4e00-\u9fff]', '', t) for t in sub]
        out.append({'start': seg['start'], 'end': seg['end'], 'text': stripped})
    return out


def build_segments(word_segments: list, removeOthersAndToList: list, textAfterLLM: list) -> list:
    """根据字级时间戳与分段文本，构建带序号的字幕分段列表"""
    segments = []
    wordi = 0
    seq = 0
    n = len(word_segments)
    for i, seg in enumerate(removeOthersAndToList):
        segEnd = seg['end']
        stripped_list = seg['text']
        display_list = textAfterLLM[i]['text']
        for j, text in enumerate(stripped_list):
            l = len(text)
            if l <= 0:
                continue
            # 确保映射不超出该段结束时间，也不越界
            while l > 0 and (wordi + l - 1 >= n or word_segments[wordi + l - 1]['end'] > segEnd):
                l -= 1
            if l <= 0:
                break
            segments.append({
                "seq": seq,
                "start": round(word_segments[wordi]['start'], 3),
                "end": round(word_segments[wordi + l - 1]['end'], 3),
                "text": display_list[j] if j < len(display_list) else text,
            })
            seq += 1
            wordi += l
        # 跳过本段剩余的字级时间戳（限制误差不跨段累计）
        while wordi < n and word_segments[wordi]['start'] < segEnd:
            wordi += 1
    return segments


def replace_word(text: str, old_word: str, new_word: str):
    """在文本中替换第一次出现的旧词，返回 (新文本, 是否成功)"""
    idx = text.find(old_word)
    if idx == -1:
        return text, False
    return text[:idx] + new_word + text[idx + len(old_word):], True


def export_srt_from_segments(segments: list, output_path: str) -> str:
    """根据已含时间戳的分段列表生成字幕文件"""
    print(f"📝 生成字幕: {output_path}")
    subs = pysrt.SubRipFile()
    for i, seg in enumerate(segments, start=1):
        start = pysrt.SubRipTime(seconds=seg['start'])
        end = pysrt.SubRipTime(seconds=seg['end'])
        item = pysrt.SubRipItem(index=i, start=start, end=end, text=seg['text'])
        subs.append(item)
    subs.save(output_path, encoding="utf-8")
    print(f"✅ 字幕文件保存成功")
    return output_path
