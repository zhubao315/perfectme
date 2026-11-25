#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》预告片（约 38s）：片头卡 + 镜头蒙太奇 + 片尾卡，配 ACE-Step 配乐 + Qwen3-TTS 台词。

输出：08-宣传物料/03-预告片/满分的我-预告片.mp4
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "08-宣传物料", "03-预告片")
TMP = os.path.join(ROOT, "build", "trailer")
CLIPS = os.path.join(ROOT, "build", "clips")
CARDS = os.path.join(ROOT, "build", "cards")
VOICE = os.path.join(ROOT, "05-音频", "配音")
BGM = os.path.join(ROOT, "build", "music.wav")
HERO_H = os.path.join(ROOT, "images", "20261010-200406-0.png")
FB = "/usr/local/share/fonts/windows/msyh.ttc"
FBD = "/usr/local/share/fonts/windows/msyhbd.ttc"
FT = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
W, H, FPS = 1920, 1080, 25

SELECT = ["01", "02", "03", "06", "08", "10", "11", "14", "15", "22", "27", "29", "32"]
SEG = 2.3
TITLE = "满分的我"
TAG = "如果所有人都喜欢那个完美的我，谁来喜欢真正的我？"
# (配音文件, 出现秒) —— 出现时间在运行时按卡片长度推算
VOICES = [("V01_旁白.wav", None), ("V04_一林.wav", None), ("V06_一林.wav", None),
          ("V17_林一.wav", None), ("V22_陈晓.wav", None), ("V26_一林.wav", None)]


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD:", " ".join(cmd)); print(r.stderr[-3000:]); sys.exit(1)


def f(p, s):
    try:
        return ImageFont.truetype(p, s, index=0)
    except Exception:
        return ImageFont.truetype(p, s)


def cover(im, size):
    tw, th = size
    r = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x = (im.width - tw) // 2; y = (im.height - th) // 2
    return im.crop((x, y, x + tw, y + th))


def vgrad(size, a, b, color):
    w, h = size
    g = Image.new("L", (1, h))
    for y in range(h):
        g.putpixel((0, y), int(a + (b - a) * y / (h - 1)))
    return Image.merge("RGBA", (*Image.new("RGB", size, color).split(), g.resize((w, h))))


def ct(d, cx, y, t, font, fill, stroke=0, sc=(0, 0, 0, 160)):
    d.text((cx, y), t, font=font, fill=fill, anchor="mm", stroke_width=stroke, stroke_fill=sc)


def card_open():
    p = os.path.join(TMP, "open.png")
    img = Image.new("RGB", (W, H), (10, 16, 28)).convert("RGBA")
    # 星点
    import random
    random.seed(7)
    d = ImageDraw.Draw(img)
    for _ in range(120):
        x, y = random.randint(0, W), random.randint(0, H)
        r = random.choice([1, 1, 1, 2])
        d.ellipse([x, y, x + r, y + r], fill=(180, 205, 235, random.randint(30, 120)))
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    d = ImageDraw.Draw(img)
    ct(d, W // 2, 330, "原创 2D 微动漫 · 校园心理成长", f(FB, 40), (200, 220, 245, 235))
    ct(d, W // 2, 500, f"《{TITLE}》", f(FT, 190), (255, 255, 255, 255), stroke=4, sc=(30, 50, 85, 200))
    ct(d, W // 2, 640, "THE PERFECT ME", f(FB, 40), (165, 195, 225, 235))
    d.line([(W // 2 - 320, 720), (W // 2 + 320, 720)], fill=(240, 200, 144, 220), width=3)
    ct(d, W // 2, 790, TAG, f(FB, 44), (235, 241, 250, 240))
    img.convert("RGB").save(p)
    return p


def card_end():
    p = os.path.join(TMP, "end.png")
    bg = cover(Image.open(HERO_H).convert("RGB"), (W, H)).filter(ImageFilter.GaussianBlur(10)).convert("RGBA")
    bg.alpha_composite(vgrad((W, H), 0, 210, (8, 12, 22)))
    bg.alpha_composite(vgrad((W, H), 120, 0, (8, 12, 22)))
    d = ImageDraw.Draw(bg)
    ct(d, W // 2, 380, f"《{TITLE}》", f(FT, 170), (255, 255, 255, 255), stroke=4, sc=(20, 40, 70, 200))
    ct(d, W // 2, 520, TAG, f(FB, 46), (238, 243, 250, 245))
    ct(d, W // 2, 660, "片长 2′31″", f(FBD, 46), (255, 236, 200, 250))
    ct(d, W // 2, 760, "敬请观看", f(FB, 40), (200, 216, 234, 240))
    bg.convert("RGB").save(p)
    return p


def img_clip(png, sec, out, fade=0.6):
    run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-t", str(sec), "-i", png,
         "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p,fade=t=in:st=0:d={fade},fade=t=out:st={sec-fade}:d={fade}",
         "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])


def clip_seg(idx, sec, out):
    run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(CLIPS, idx + ".mp4"),
         "-t", str(sec), "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", out])


def main():
    os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
    op = card_open(); ep = card_end()
    open_sec, end_sec = 3.2, 5.0
    open_mp4 = os.path.join(TMP, "open.mp4"); end_mp4 = os.path.join(TMP, "end.mp4")
    img_clip(op, open_sec, open_mp4); img_clip(ep, end_sec, end_mp4)
    segs = [open_mp4]
    for i, idx in enumerate(SELECT):
        p = os.path.join(TMP, f"s{i:02d}.mp4")
        clip_seg(idx, SEG, p); segs.append(p)
    segs.append(end_mp4)
    with open(os.path.join(TMP, "list.txt"), "w") as fh:
        for s in segs:
            fh.write(f"file '{s}'\n")
    visual = os.path.join(TMP, "visual.mp4")
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
         "-i", os.path.join(TMP, "list.txt"), "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), visual])

    T = open_sec + SEG * len(SELECT) + end_sec
    # 语音出现时间
    t_voice = [1.0, open_sec + 0.3, open_sec + SEG * 4 + 0.2, open_sec + SEG * 7 + 0.2,
               open_sec + SEG * 10 + 0.2, T - end_sec + 0.6]
    inputs = ["-i", visual, "-i", BGM]
    for name, _ in VOICES:
        inputs += ["-i", os.path.join(VOICE, name)]
    fc = [f"[1:a]atrim=30:{30+T},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.5,"
          f"afade=t=out:st={T-3}:d=3,volume=0.5[bgm]"]
    labels = ["[bgm]"]
    for k, (name, _) in enumerate(VOICES):
        ms = int(t_voice[k] * 1000)
        fc.append(f"[{2+k}:a]adelay={ms}|{ms},volume=1.0[v{k}]")
        labels.append(f"[v{k}]")
    fc.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.95[a]")
    out = os.path.join(OUT, "满分的我-预告片.mp4")
    run(["ffmpeg", "-y", "-v", "error", *inputs,
         "-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
         "-shortest", out])
    print("trailer:", out, f"~{T:.1f}s")


if __name__ == "__main__":
    main()
