import ffmpeg
import os
import shutil
import subprocess

_FFMPEG_BIN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin")


def _get_ffmpeg_exe():
    """优先使用项目自带 ffmpeg，否则回退到系统 PATH 中的 ffmpeg"""
    local = os.path.join(_FFMPEG_BIN_DIR, "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    return "ffmpeg"


def embed_subtitle(video_path, subtitle_path, output_path, language="zh"):
    """将字幕烧录到视频画面中（硬编码）"""
    print(f"🎬 烧录字幕到画面: {video_path}")
    print(f"📝 字幕文件: {subtitle_path}")
    print(f"💾 输出文件: {output_path}")

    try:
        # 正确的滤镜字符串构造 - 使用ffmpeg-python的filter方法
        (
            ffmpeg
            .input(video_path)
            .filter('subtitles', subtitle_path,
                    force_style='FontSize=20,OutlineColour=&H80000000,PrimaryColour=&HFFFFFF,FontName=\'Microsoft YaHei\'')
            .output(
                output_path,
                acodec='copy',
                vcodec='libx264',
                preset='medium',
                crf=23,
                pix_fmt='yuv420p'
            )
            .run(overwrite_output=True, quiet=True)
        )

        print(f"✅ 字幕烧录成功")
        return output_path

    except ffmpeg.Error as e:
        print(f"❌ 烧录失败: {e.stderr.decode() if e.stderr else str(e)}")
        raise


def embed_subtitle_from_config(video_path, subtitle_path, output_path, style=None, ffmpeg_cfg=None):
    """根据配置文件烧录字幕"""
    print(f"🎬 烧录字幕到画面: {video_path}")
    style = style or {}
    ffmpeg_cfg = ffmpeg_cfg or {}

    force_style = (
        f"FontSize={style.get('font_size', 20)},"
        f"FontName={style.get('font_name', 'Microsoft YaHei')},"
        f"PrimaryColour={style.get('primary_color', '&HFFFFFF')},"
        f"OutlineColour={style.get('outline_color', '&H80000000')},"
        f"MarginV={style.get('margin_v', 20)},"
        f"Outline={style.get('outline', 2)},"
        f"Shadow={style.get('shadow', 1)}"
    )

    out_dir = os.path.dirname(os.path.abspath(output_path)) or "."
    os.makedirs(out_dir, exist_ok=True)

    # 拷贝字幕到输出目录下的固定安全文件名，避免 Windows 绝对路径（盘符冒号、反斜杠）
    # 在 subtitles 滤镜中的转义问题
    safe_srt = os.path.join(out_dir, "_subtitle.srt")
    shutil.copyfile(subtitle_path, safe_srt)

    # 使用相对文件名 + 将 cwd 设为输出目录，彻底规避滤镜路径转义
    filter_str = f"subtitles=_subtitle.srt:force_style='{force_style}'"

    cmd = [
        _get_ffmpeg_exe(), "-y",
        "-i", video_path,
        "-vf", filter_str,
        "-c:a", "copy",
        "-c:v", ffmpeg_cfg.get("vcodec", "libx264"),
        "-preset", ffmpeg_cfg.get("preset", "medium"),
        "-crf", str(ffmpeg_cfg.get("crf", 23)),
        "-pix_fmt", ffmpeg_cfg.get("pix_fmt", "yuv420p"),
        output_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, cwd=out_dir)
    except FileNotFoundError:
        raise RuntimeError("未找到 ffmpeg，请确认 bin 目录下的 ffmpeg.exe 存在，或已将 ffmpeg 加入系统 PATH")

    if result.returncode != 0:
        stderr = (result.stderr or b"").decode("utf-8", "replace")
        raise RuntimeError(f"ffmpeg 烧录失败: {stderr[-2000:]}")

    print(f"✅ 字幕烧录成功")
    return output_path


def embed_subtitle_with_style(video_path, subtitle_path, output_path,
                              font_size=24, font_name="Microsoft YaHei",
                              primary_color='&HFFFFFF', outline_color='&H80000000',
                              margin_v=20):
    """带样式参数的字幕烧录"""
    print(f"🎬 烧录字幕到画面: {video_path}")

    try:
        # 构造样式字符串 - 注意引号的使用
        style = f"FontSize={font_size},FontName='{font_name}',PrimaryColour={primary_color},OutlineColour={outline_color},MarginV={margin_v},Outline=2,Shadow=1"

        # 使用filter方法，这是ffmpeg-python推荐的方式
        (
            ffmpeg
            .input(video_path)
            .filter('subtitles', subtitle_path, force_style=style)
            .output(
                output_path,
                acodec='copy',
                vcodec='libx264',
                preset='slow',
                crf=18,
                pix_fmt='yuv420p'
            )
            .run(overwrite_output=True, quiet=True)
        )

        print(f"✅ 字幕烧录成功")
        return output_path

    except ffmpeg.Error as e:
        print(f"❌ 烧录失败: {e.stderr.decode() if e.stderr else str(e)}")
        raise


def embed_subtitle_with_filter(video_path, subtitle_path, output_path):
    """使用ffmpeg-python的filter方法的正确方式"""
    print(f"🎬 烧录字幕到画面: {video_path}")

    try:
        # 方式1：使用filter方法，传入参数
        video = ffmpeg.input(video_path)
        video = ffmpeg.filter(video, 'subtitles', subtitle_path,
                              force_style='FontSize=20,OutlineColour=&H80000000,PrimaryColour=&HFFFFFF,FontName=\'Microsoft YaHei\'')
        video = ffmpeg.output(video, output_path,
                              acodec='copy',
                              vcodec='libx264',
                              preset='medium',
                              crf=23)
        ffmpeg.run(video, overwrite_output=True, quiet=True)

        print(f"✅ 字幕烧录成功")
        return output_path

    except ffmpeg.Error as e:
        print(f"❌ 烧录失败: {e.stderr.decode() if e.stderr else str(e)}")
        raise


# 你的调用代码
def process_video_with_subtitle(video_path, output_dir):
    """处理视频：自动查找同名字幕文件并烧录"""
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    subtitle_path = os.path.join(output_dir, f"{base_name}.srt")
    output_video_path = os.path.join(output_dir, f"{base_name}_sub.mp4")

    # 检查字幕文件是否存在
    if not os.path.exists(subtitle_path):
        print(f"⚠️ 字幕文件不存在: {subtitle_path}")
        return None

    # 调用修正后的函数
    return embed_subtitle(video_path, subtitle_path, output_video_path)


# 使用示例
if __name__ == "__main__":
    # 示例1：直接调用
    video_path = "input.mp4"
    output_dir = "."

    # 方法1：使用基础版本
    base_name = os.path.splitext(os.path.basename(video_path))[0]
    subtitle_path = os.path.join(output_dir, f"{base_name}.srt")
    output_video_path = os.path.join(output_dir, f"{base_name}_sub.mp4")

    # 这会正常工作
    embed_subtitle(video_path, subtitle_path, output_video_path)

    # 方法2：使用带样式的版本
    embed_subtitle_with_style(
        video_path,
        subtitle_path,
        output_video_path,
        font_size=24,
        font_name="SimHei",
        primary_color='&HFF0000'  # 红色
    )

    # 方法3：使用你的调用模式
    process_video_with_subtitle("input.mp4", ".")

#
# import ffmpeg
#
# def embed_subtitle(video_path, subtitle_path, output_path, language="zh"):
#     """嵌入字幕"""
#     print(f"🎬 嵌入字幕: {video_path}")
#     try:
#         video = ffmpeg.input(video_path)
#         subtitle = ffmpeg.input(subtitle_path)
#
#         ffmpeg.output(
#             video,
#             subtitle,
#             output_path,
#             vcodec='copy',
#             acodec='copy',
#             scodec='mov_text',
#             **{'metadata:s:s:0': f'language={language}'}
#         ).run(overwrite_output=True, quiet=True)
#
#         print(f"✅ 字幕嵌入成功")
#         return output_path
#
#     except ffmpeg.Error as e:
#         print(f"❌ 嵌入失败: {e.stderr.decode()}")
#         raise

