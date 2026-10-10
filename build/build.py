#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》微动漫合成脚本（轻薄半赛璐·淡彩赛璐 版）
图像 -> Ken Burns 动态化 -> 拼接 -> 烧入字幕 -> 混入环境音乐 -> 片尾电影滚动字幕 -> 输出 mp4
"""
import os, subprocess, shutil, sys, json

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from scene import SHOTS, TR

ROOT = "/oc/mov"
IMG = os.path.join(ROOT, "04-分镜图")
BUILD = os.path.join(ROOT, "build")
CLIPS = os.path.join(BUILD, "clips")
SEGS = os.path.join(BUILD, "segments")
CARDS = os.path.join(BUILD, "cards")
OUT = os.path.join(ROOT, "07-成片")
FPS = 25
W, H = 1920, 1080

def font():
    r = subprocess.run(["fc-match", "-f", "%{file}", "Microsoft YaHei"],
                       capture_output=True, text=True)
    return r.stdout.strip()

FONT = font()
SERIF = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
if not os.path.exists(SERIF):
    SERIF = FONT

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMDLINE:", " ".join(cmd))
        print("STDERR:", r.stderr[-2000:])
        sys.exit(1)

def pfont(path, size):
    try:
        return ImageFont.truetype(path, size, index=0)
    except Exception:
        return ImageFont.truetype(path, size)

def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

def make_card(name, lines):
    """lines: list of (text, fontsize, y, color)"""
    path = os.path.join(CARDS, name)
    filters = []
    for text, fs, y, color in lines:
        filters.append(
            f"drawtext=fontfile='{FONT}':text='{esc(text)}':fontcolor={color}:"
            f"fontsize={fs}:x=(w-text_w)/2:y={y}")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", "color=c=0x101a24:s=1920x1080",
         "-frames:v", "1", "-vf", ",".join(filters), path])
    return path

def gradient_overlay(base):
    """在片名背景上叠加柔和的暗色渐变，保证文字可读且保留水彩纸纹"""
    w, h = base.size
    ov = Image.new("L", (w, h), 0)
    px = ov.load()
    for y in range(h):
        ty = y / h
        top = 255 * max(0.0, (0.42 - ty) / 0.42) ** 1.2
        bot = 255 * max(0.0, (ty - 0.55) / 0.45) ** 1.2
        v = int(min(210, 90 + max(top, bot) * 0.9))
        for x in range(w):
            px[x, y] = v
    ov = ov.filter(ImageFilter.GaussianBlur(60))
    dark = Image.new("RGB", (w, h), (10, 15, 22))
    return Image.composite(dark, base, ov.point(lambda p: int(p * 0.72)))

def draw_heart(d, cx, cy, r, fill):
    """小爱心（呼应点赞红）"""
    d.ellipse([cx - r, cy - r, cx, cy + r * 0.1], fill=fill)
    d.ellipse([cx, cy - r, cx + r, cy + r * 0.1], fill=fill)
    d.polygon([(cx - r * 0.98, cy - r * 0.1),
               (cx + r * 0.98, cy - r * 0.1),
               (cx, cy + r * 1.25)], fill=fill)

def make_title_card():
    """片头字幕卡：淡彩赛璐教室背景 + 主题化艺术片名（满分红圈 + 点赞爱心 + 青蓝辉光）"""
    base = Image.open(os.path.join(IMG, "场景/开场背景.png")).convert("RGB").resize((W, H))
    canvas = gradient_overlay(base)

    title = "满分的我"
    size, gap, ty = 186, 52, 236
    tf = pfont(SERIF, size)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8), (0, 0, 0)))
    ws = [probe.textlength(ch, font=tf) for ch in title]
    total = sum(ws) + gap * (len(title) - 1)
    xs, x = [], W / 2 - total / 2
    for w in ws:
        xs.append(x)
        x += w + gap

    # 青蓝辉光：呼应虚拟自我"一林"
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for ch, xx in zip(title, xs):
        gd.text((xx, ty), ch, font=tf, fill=(127, 216, 255, 205))
    glow = glow.filter(ImageFilter.GaussianBlur(32))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), glow).convert("RGB")

    # 落影，抬升文字
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for ch, xx in zip(title, xs):
        sd.text((xx + 5, ty + 9), ch, font=tf, fill=(5, 9, 15, 215))
    sh = sh.filter(ImageFilter.GaussianBlur(13))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), sh).convert("RGB")
    d = ImageDraw.Draw(canvas)

    # 主字：满分=理想(冷白) · 的=过渡(淡灰) · 我=真实(暖金)
    colors = [(255, 255, 255), (255, 255, 255), (206, 218, 232), (240, 200, 144)]
    for ch, xx, col in zip(title, xs, colors):
        d.text((xx, ty), ch, font=tf, fill=col)

    # "我"右上角爱心（点赞红）
    draw_heart(d, xs[3] + ws[3] + 6, ty - 22, 17, (255, 90, 95))

    def ctext(text, size, y, color, font_path=FONT):
        f = pfont(font_path, size)
        bb = d.textbbox((0, 0), text, font=f)
        w = bb[2] - bb[0]
        d.text(((W - w) / 2 - bb[0], y), text, font=f, fill=color)

    ctext("原创校园心理微动漫", 42, 156, (150, 175, 196))
    ctext("The Perfect Me", 38, 466, (176, 198, 218))
    ctext("如果所有人都喜欢那个完美的我，", 46, 560, (200, 214, 228))
    ctext("谁来喜欢真正的我？", 46, 626, (200, 214, 228))
    ctext("高一 1 班 · 朱 明 萱", 52, 748, (240, 200, 144))

    path = os.path.join(CARDS, "title.png")
    canvas.save(path)
    return path

def make_end_card():
    """片尾定格卡：居中的"感谢观看"，停在最后一帧"""
    canvas = Image.new("RGB", (W, H), (11, 15, 20))
    d = ImageDraw.Draw(canvas)

    def ctext(text, size, y, color, font_path=FONT):
        f = pfont(font_path, size)
        bb = d.textbbox((0, 0), text, font=f)
        w = bb[2] - bb[0]
        d.text(((W - w) / 2 - bb[0], y), text, font=f, fill=color)

    ctext("感 谢 观 看", 122, 420, (255, 255, 255), SERIF)
    d.line([(W / 2 - 230, 594), (W / 2 + 230, 594)], fill=(240, 200, 144), width=2)
    ctext("Thank you for watching", 40, 632, (176, 198, 218))
    draw_heart(d, W / 2, 726, 18, (255, 90, 95))
    ctext("《满分的我》 · 高一 1 班 朱明萱", 36, 760, (150, 175, 196))

    path = os.path.join(CARDS, "end_thanks.png")
    canvas.save(path)
    return path

def still_card_clip(src, dur, idx, fade_in=1.2):
    """静态定格片段（无运动、无淡出，结束停在最后一帧）"""
    dst = os.path.join(CLIPS, f"{idx:02d}.mp4")
    vf = f"scale={W}:{H},format=yuv420p"
    if fade_in:
        vf += f",fade=t=in:st=0:d={fade_in}"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-loop", "1", "-t", str(dur), "-i", src, "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-r", str(FPS), "-pix_fmt", "yuv420p", dst])
    return dst

def probe_dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def make_light_overlay():
    """柔和漫射空气光：偏冷的柔白径向渐变，透明边缘，用于缓慢漂移（空气感）。"""
    w, h = 2160, 1215
    cx, cy = w * 0.60, h * 0.34
    maxr = w * 0.72
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = img.load()
    for y in range(h):
        dy = (y - cy) ** 2
        for x in range(w):
            d = (dy + (x - cx) ** 2) ** 0.5
            a = 1.0 - d / maxr
            if a <= 0:
                continue
            a = a * a * 255 * 0.9
            px[x, y] = (216, 226, 236, int(a))
    img = img.filter(ImageFilter.GaussianBlur(36))
    path = os.path.join(CARDS, "light.png")
    img.save(path)
    return path

def make_paper_overlay():
    """纸张颗粒纹理：中性灰细噪，用 softlight + 亮度蒙版混入（仅亮部出纸感，暗部干净）。"""
    w, h = 1920, 1080
    rnd = os.urandom(w * h)
    buf = bytearray(w * h)
    for i in range(w * h):
        v = 128 + int((rnd[i] - 128) * 0.16)
        buf[i] = 0 if v < 0 else (255 if v > 255 else v)
    img = (Image.frombytes("L", (w, h), bytes(buf))
           .filter(ImageFilter.GaussianBlur(1.8)).convert("RGB"))
    path = os.path.join(CARDS, "paper.png")
    img.save(path)
    return path

SUBS = []  # (start, end, style, text)

# ---- 轻动画镜头运动：慢推/慢拉/慢移 + sin 呼吸（空间在呼吸，而非整图平移）----
def _motion_expr(motion, n):
    cx = "iw/2-(iw/zoom/2)"
    cy = "ih/2-(ih/zoom/2)"
    if motion == "in":       # 缓慢推近 + 轻微呼吸
        z = f"1.02+0.05*on/{n}+0.005*sin(on/34)"
        x = f"{cx}+7*sin(on/47)"; y = f"{cy}+5*cos(on/53)"
    elif motion == "out":    # 缓慢拉远 + 轻微呼吸
        z = f"1.07-0.05*on/{n}+0.005*sin(on/31)"
        x = f"{cx}+7*sin(on/43)"; y = f"{cy}+5*cos(on/49)"
    elif motion == "pan":    # 慢移（横）+ 轻微上下浮动
        z = "1.06"
        x = f"(iw-iw/zoom)*on/{n}"; y = f"{cy}+6*sin(on/45)"
    else:                    # hold：极轻呼吸，几乎静止
        z = "1.035+0.007*sin(on/42)"
        x = f"{cx}+5*sin(on/51)"; y = f"{cy}+4*cos(on/57)"
    return z, x, y

def clip(src, dur, motion, idx):
    n = max(1, int(round(dur * FPS)))
    z, x, y = _motion_expr(motion, n)
    dst = os.path.join(CLIPS, f"{idx:02d}.mp4")
    vf = (f"scale=2496:1404,zoompan=z='{z}':d=1:x='{x}':y='{y}':"
          f"s={W}x{H}:fps={FPS},format=yuv420p")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-loop", "1", "-t", f"{dur}", "-i", src, "-vf", vf,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-r", str(FPS), "-pix_fmt", "yuv420p", dst])
    return dst

def clip2(src_a, src_b, dur, motion, idx):
    """缓动镜头：一镜内在中点做一次交叉溶解，从姿势/表情 A 过渡到 B（微笑/苦恼/动作）。"""
    half = dur / 2.0
    d_a = half + TR / 2.0
    d_b = half + TR / 2.0
    n_a = max(1, int(round(d_a * FPS)))
    n_b = max(1, int(round(d_b * FPS)))
    za, xa, ya = _motion_expr(motion, n_a)
    zb, xb, yb = _motion_expr(motion, n_b)
    off = d_a - TR
    dst = os.path.join(CLIPS, f"{idx:02d}.mp4")
    fc = (f"[0:v]scale=2496:1404,zoompan=z='{za}':d=1:x='{xa}':y='{ya}':"
          f"s={W}x{H}:fps={FPS},format=yuv420p[a];"
          f"[1:v]scale=2496:1404,zoompan=z='{zb}':d=1:x='{xb}':y='{yb}':"
          f"s={W}x{H}:fps={FPS},format=yuv420p[b];"
          f"[a][b]xfade=transition=fade:duration={TR}:offset={off:.3f},format=yuv420p[o]")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-loop", "1", "-t", f"{d_a:.3f}", "-i", src_a,
         "-loop", "1", "-t", f"{d_b:.3f}", "-i", src_b,
         "-filter_complex", fc, "-map", "[o]",
         "-t", f"{dur:.3f}", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-r", str(FPS), "-pix_fmt", "yuv420p", dst])
    return dst

def color_clip(color, dur, idx):
    dst = os.path.join(CLIPS, f"{idx:02d}.mp4")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:r={FPS}",
         "-t", f"{dur}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", dst])
    return dst

def ass_time(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"

# 字幕呼吸：按样式给锚点(对齐, y)与复位色
ANCHOR = {"Sub": (2, 1002, "&HFFFFFF&"),
          "Narr": (2, 1002, "&HE6D8BC&"),
          "Quote": (5, 540, "&HFFFFFF&")}
# 需要「慢慢变暖色」的关键词
KEYWORDS = ["完美", "不完美", "满分", "优秀", "自律", "喜欢", "喜欢自己",
            "接纳", "真实的", "真正的", "自己", "不够好", "被喜欢"]

def highlight(text, reset):
    for kw in KEYWORDS:
        if kw in text:
            text = text.replace(kw, f"{{\\c&H90C8F0&}}{kw}{{{reset}}}")
    return text

HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Microsoft YaHei,52,&H00FFFFFF,&H000000FF,&H00202020,&H64000000,0,0,0,0,100,100,0,0,1,2.6,0.6,2,100,100,64,1
Style: Narr,Microsoft YaHei,48,&H00E6D8BC,&H000000FF,&H00202020,&H64000000,0,-1,0,0,100,100,0,0,1,2.4,0.5,2,140,140,70,1
Style: Quote,Microsoft YaHei,60,&H00FFFFFF,&H000000FF,&H00101820,&H00000000,0,0,0,0,100,100,0,0,1,3,0,5,120,120,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def write_ass(path):
    """字幕改为「淡入 + 轻微上浮 + 关键词渐暖」的文字呼吸效果，避免硬切。"""
    lines = [HEADER]
    for start, end, style, text in SUBS:
        text = text.replace("\n", "\\N")
        an, y0, reset = ANCHOR.get(style, (2, 1002, "&HFFFFFF&"))
        text = highlight(text, reset)
        y1 = y0 + 14
        pre = f"{{\\an{an}\\fad(450,450)\\move(960,{y1},960,{y0},0,600)}}"
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{pre}{text}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def add_subs(t0, subs):
    for rel_s, rel_e, style, text in subs:
        if text:
            SUBS.append((t0 + rel_s, t0 + rel_e, style, text))

def build_music(total):
    """三段原创配乐（ACE-Step 纯器乐）：开场(冷·悬疑) → 冲突(紧张) → 结尾(暖·希望)。
    交叉淡化后铺满全片，首尾淡入淡出。"""
    a = os.path.join(BUILD, "ace/opening.flac")
    b = os.path.join(BUILD, "ace/conflict.flac")
    c = os.path.join(BUILD, "ace/ending.flac")
    music = os.path.join(BUILD, "music.wav")
    fmt = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", a, "-i", b, "-i", c, "-filter_complex",
         f"[0]{fmt}[a0];[1]{fmt}[a1];[2]{fmt}[a2];"
         "[a0][a1]acrossfade=d=3:c1=tri:c2=tri[x];[x][a2]acrossfade=d=3:c1=tri:c2=tri[y];"
         f"[y]afade=t=in:st=0:d=3,afade=t=out:st={total-6}:d=6,volume=1.0[out]",
         "-map", "[out]", "-t", str(total), music])
    return music

# ------------------------- 片尾电影滚动字幕 -------------------------

CREDITS = [
    ("h", "满 分 的 我", 118, (255, 255, 255), SERIF, 0),
    ("s", "The Perfect Me", 40, (170, 190, 210), FONT, 8),
    ("q", "如果所有人都喜欢那个完美的我，谁来喜欢真正的我？", 38, (190, 205, 220), FONT, 20),
    ("gap", 60),
    ("h", "编 剧 · 导 演 · 分 镜 · 美 术", 40, (240, 200, 144), FONT, 0),
    ("b", "朱 明 萱", 56, (255, 255, 255), SERIF, 14),
    ("s", "高一 1 班", 36, (170, 190, 210), FONT, 20),
    ("gap", 66),
    ("h", "本片揭示的 心理学理念", 42, (240, 200, 144), FONT, 0),
    ("b", "自 我 差 异 理 论", 64, (255, 255, 255), SERIF, 16),
    ("s", "Self-Discrepancy Theory", 38, (170, 200, 224), FONT, 6),
    ("s", "E. Tory Higgins · 1987", 34, (150, 175, 196), FONT, 12),
    ("b", "现实自我（Actual Self）", 38, (205, 220, 235), FONT, 22),
    ("b", "理想自我（Ideal Self）", 38, (205, 220, 235), FONT, 10),
    ("b", "应该自我（Ought Self）", 38, (205, 220, 235), FONT, 10),
    ("s", "当现实自我与理想、应该自我出现落差，", 36, (190, 205, 220), FONT, 26),
    ("s", "可能带来失望、焦虑与内疚——", 36, (190, 205, 220), FONT, 8),
    ("s", "但落差本身，不等于你不值得被爱。", 38, (240, 200, 144), FONT, 12),
    ("gap", 66),
    ("h", "制 作 工 具 与 组 件", 42, (240, 200, 144), FONT, 0),
    ("b", "图像生成　·　Qwen-Image-2.1", 38, (205, 220, 235), FONT, 16),
    ("b", "绘修　　　·　Krita", 38, (205, 220, 235), FONT, 10),
    ("b", "动画　　　·　OpenToonz", 38, (205, 220, 235), FONT, 10),
    ("b", "剪辑合成　·　Kdenlive / MLT", 38, (205, 220, 235), FONT, 10),
    ("b", "影音合成　·　FFmpeg", 38, (205, 220, 235), FONT, 10),
    ("b", "字幕　　　·　ASS (Advanced SubStation)", 38, (205, 220, 235), FONT, 10),
    ("b", "原创配乐　·　ACE-Step 原创生成", 38, (205, 220, 235), FONT, 10),
    ("b", "字体　　　·　思源宋体 / 微软雅黑", 38, (205, 220, 235), FONT, 10),
    ("s", "本地 AI 智能体协助制作 · 全流程原创", 34, (150, 175, 196), FONT, 18),
    ("gap", 66),
    ("s", "感谢每一个愿意喜欢真实我们的人", 36, (190, 205, 220), FONT, 0),
    ("gap", 56),
    ("h", "给 大 家 最 好 的 祝 福", 44, (240, 200, 144), FONT, 0),
    ("b", "愿你被这个世界温柔以待", 42, (255, 255, 255), FONT, 20),
    ("b", "愿你努力，也允许自己休息", 42, (255, 255, 255), FONT, 12),
    ("b", "愿你不必满分，也值得被爱", 42, (240, 200, 144), FONT, 12),
    ("b", "愿所有真实的你，都被看见、被喜欢", 42, (255, 255, 255), FONT, 12),
    ("gap", 60),
    ("s", "你可以努力成为更好的自己，但不必完美，才值得被喜欢。", 40, (190, 205, 220), FONT, 10),
    ("gap", 70),
    ("s", "本片为原创校园心理微动漫，角色 / 剧情 / 分镜 / 提示词均为原创", 32, (140, 165, 190), FONT, 0),
    ("s", "© 2026  高一 1 班 · 朱明萱 ·《满分的我》", 34, (150, 175, 196), FONT, 14),
    ("s", "原创作品 · 请勿盗用", 30, (120, 145, 170), FONT, 12),
]

def make_credits_image():
    """生成一张透明背景的长图（片尾滚动内容），返回 (path, height)"""
    pad_top, pad_bottom = 60, 60
    d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    y = pad_top
    layout = []
    for item in CREDITS:
        if item[0] == "gap":
            y += item[1]
            continue
        _, text, size, color, fpath, gap = item
        f = pfont(fpath, size)
        bb = d.textbbox((0, 0), text, font=f)
        h = bb[3] - bb[1]
        layout.append((text, f, color, y, h))
        y += size + gap
    total_h = y + pad_bottom

    img = Image.new("RGBA", (W, total_h), (0, 0, 0, 0))
    dd = ImageDraw.Draw(img)
    for text, f, color, yy, h in layout:
        bb = dd.textbbox((0, 0), text, font=f)
        wtext = bb[2] - bb[0]
        dd.text(((W - wtext) / 2 - bb[0], yy - bb[1]), text, font=f,
                fill=color + (255,))
    path = os.path.join(CARDS, "credits.png")
    img.save(path)
    return path, total_h

def credits_clip(idx, target=11.0):
    img, ch = make_credits_image()
    dur = target
    dst = os.path.join(CLIPS, f"{idx:02d}.mp4")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"color=c=0x0b0f14:s={W}x{H}:r={FPS}",
         "-loop", "1", "-i", img, "-filter_complex",
         f"[1:v]format=rgba[c];[0:v][c]overlay=x=0:"
         f"y='{H}-({H}+{ch})*t/{dur:.3f}':format=auto,"
         f"fade=t=in:st=0:d=1.5,fade=t=out:st={dur-2:.3f}:d=2,format=yuv420p[v]",
         "-map", "[v]", "-t", f"{dur:.3f}", "-c:v", "libx264",
         "-preset", "veryfast", "-crf", "20", "-r", str(FPS),
         "-pix_fmt", "yuv420p", dst])
    return dst, dur

def main():
    for d in (CLIPS, SEGS, CARDS, OUT):
        os.makedirs(d, exist_ok=True)
    for old in os.listdir(CLIPS):
        if old.endswith(".mp4"):
            os.remove(os.path.join(CLIPS, old))
    for old in os.listdir(SEGS):
        os.remove(os.path.join(SEGS, old))

    card_title = make_title_card()
    card_e1 = make_card("end1.png", [
        ("你可以努力成为更好的自己，", 62, 470, "white"),
        ("但不必完美，才值得被喜欢。", 62, 570, "0xf0c890"),
    ])

    # ---- 场景表见 build/scene.py（镜头 / 台词 / 音效 单一事实源）----
    idx = 0
    k = 0
    t = 0.0
    concat_list = []
    timeline = {}
    for sh in SHOTS:
        sid, src, dur, motion, subs = sh["id"], sh["src"], sh["dur"], sh["motion"], sh["subs"]
        src2 = sh.get("src2")
        if src == "#black":
            p = color_clip("black", dur, idx)
        elif src == "#title":
            p = clip(card_title, dur, motion, idx)
        elif src == "#e1":
            p = clip(card_e1, dur, motion, idx)
        elif src2:
            p = clip2(os.path.join(IMG, src), os.path.join(IMG, src2), dur, motion, idx)
        else:
            p = clip(os.path.join(IMG, src), dur, motion, idx)
        concat_list.append(p)
        new_start = t - k * TR
        timeline[sid] = round(new_start, 3)
        add_subs(new_start, subs)
        t += dur
        idx += 1
        k += 1

    with open(os.path.join(BUILD, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    # ---- 片尾电影滚动字幕 ----
    credits, dur_c = credits_clip(idx, target=9.0)
    concat_list.append(credits)
    t += dur_c
    idx += 1

    # ---- 片尾定格：居中"感谢观看"，停在最后一帧 ----
    end_card = make_end_card()
    p = still_card_clip(end_card, 3.0, idx, fade_in=1.2)
    concat_list.append(p)
    t += 3.0
    idx += 1

    total = t
    print(f"镜头数={idx}  硬切总长={total:.1f}s")

    # ---- 交叉溶解合成（避免整图硬切）----
    # 分段实现：每段「主体(middle，直通)」+「0.5s 手写交叉淡化(transition)」，
    # 最后 concat -c copy。避免 ffmpeg xfade 的逐帧噪声与多次 rgba 往返的累积噪声。
    durs = [probe_dur(p) for p in concat_list]
    n = len(concat_list)

    mids = []
    for i, p in enumerate(concat_list):
        head = TR if i > 0 else 0.0
        tail = TR if i < n - 1 else 0.0
        seg = max(0.05, durs[i] - head - tail)
        mid = os.path.join(SEGS, f"mid{i:02d}.mp4")
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{head:.3f}", "-i", p, "-t", f"{seg:.3f}",
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
             "-r", str(FPS), "-pix_fmt", "yuv420p", mid])
        mids.append(mid)

    trans = []
    for i in range(n - 1):
        tr = os.path.join(SEGS, f"tr{i:02d}.mp4")
        run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-ss", f"{durs[i] - TR:.3f}", "-i", concat_list[i], "-t", f"{TR:.3f}",
             "-ss", "0", "-i", concat_list[i + 1], "-t", f"{TR:.3f}",
             "-filter_complex",
             "[0:v]format=rgba[a];[1:v]format=rgba,"
             f"fade=t=in:st=0:d={TR}:alpha=1[b];"
             "[a][b]overlay=0:0,format=yuv420p[o]",
             "-map", "[o]", "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "20", "-r", str(FPS), "-pix_fmt", "yuv420p", tr])
        trans.append(tr)

    ordered = []
    for i in range(n):
        ordered.append(mids[i])
        if i < n - 1:
            ordered.append(trans[i])
    total = sum(durs) - (n - 1) * TR
    print(f"交叉溶解后总长={total:.1f}s")

    visual = os.path.join(BUILD, "visual.mp4")
    clist = os.path.join(BUILD, "concat.txt")
    with open(clist, "w") as f:
        for p in ordered:
            f.write(f"file '{p}'\n")
    with open(os.path.join(BUILD, "segments.txt"), "w") as f:
        f.write("\n".join(ordered) + "\n")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-f", "concat", "-safe", "0", "-i", clist, "-c", "copy", visual])

    # subtitles
    ass = os.path.join(BUILD, "subs.ass")
    write_ass(ass)

    # music
    music = build_music(total)

    # 空气感 + 纸感（分层微动）：柔和漫射光缓慢漂移 + 受亮度约束的纸纹颗粒，再烧入呼吸字幕
    light = make_light_overlay()
    paper = make_paper_overlay()
    out = os.path.join(OUT, "高一1班-朱明萱-满分的我.mp4")
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
         "-i", visual, "-loop", "1", "-i", light, "-loop", "1", "-i", paper, "-i", music,
         "-filter_complex",
         "[0:v]scale=1920:1080,format=yuv420p[base];"
         "[base]split[b0][b1];[b1]format=rgb24[b1r];"
         "[2:v]scale=1920:1080,format=rgb24[g];"
         "[b1r][g]blend=all_mode=softlight:all_opacity=0.6[grr];"
         "[grr]format=yuv420p[gr];"
         "[base]format=gray,lut=y='if(lt(val,96),0,pow((val-96)/159\\,0.7)*255)'[m];"
         "[b0][gr][m]maskedmerge[bg];"
         "[1:v]scale=2160:1215,format=rgba,colorchannelmixer=aa=0.08[lgt];"
         "[bg][lgt]overlay=x='-120+70*sin(t*0.07)':y='-70+45*cos(t*0.055)':format=auto[b2];"
         f"[b2]subtitles='{ass}'[v]",
         "-map", "[v]", "-map", "3:a",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", "-shortest", out])
    print("成片:", out)

if __name__ == "__main__":
    main()
