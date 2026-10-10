#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》宣传物料生成：主海报 / 横版主视觉 / 角色卡 / 剧照九宫格 / 展架 / 信息卡

素材：04-分镜图（原创）+ 本地 Qwen-Image-2.1 生成的主视觉（images/）
输出：08-宣传物料/
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = "/oc/mov"
OUT = os.path.join(ROOT, "08-宣传物料")
VIS = os.path.join(OUT, "01-主视觉")
IMG = os.path.join(ROOT, "images")
SHOTS = os.path.join(ROOT, "04-分镜图", "镜头")
CHARS = os.path.join(ROOT, "04-分镜图", "角色")

HERO_V = os.path.join(IMG, "20261010-200445-0.png")  # 竖版主视觉
HERO_H = os.path.join(IMG, "20261010-200406-0.png")  # 横版主视觉

FB = "/usr/local/share/fonts/windows/msyh.ttc"
FT = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
FBD = "/usr/local/share/fonts/windows/msyhbd.ttc"
if not os.path.exists(FBD):
    FBD = FB

TITLE = "满分的我"
EN = "THE PERFECT ME"
TAG = "如果所有人都喜欢那个完美的我，谁来喜欢真正的我？"
CREDIT = "微动漫 · 校园心理成长 ｜ 高一1班 · 朱明萱 ｜ 片长 3′30″"
TOOLS = "原创图像 Qwen-Image-2.1 · 配乐 ACE-Step · 配音 Qwen3-TTS · 绘修 Krita · 动画 OpenToonz · 剪辑 Kdenlive/FFmpeg"


def f(path, size):
    try:
        return ImageFont.truetype(path, size, index=0)
    except Exception:
        return ImageFont.truetype(path, size)


def cover(im, size):
    tw, th = size
    r = max(tw / im.width, th / im.height)
    im = im.resize((int(im.width * r + 1), int(im.height * r + 1)), Image.LANCZOS)
    x = (im.width - tw) // 2
    y = (im.height - th) // 2
    return im.crop((x, y, x + tw, y + th))


def lighten(c, f=0.6):
    return tuple(int(x + (255 - x) * f) for x in c)


def vgrad(size, top_a, bot_a, color=(8, 14, 26)):
    w, h = size
    g = Image.new("L", (1, h))
    for y in range(h):
        t = y / (h - 1)
        g.putpixel((0, y), int(top_a + (bot_a - top_a) * t))
    g = g.resize((w, h))
    layer = Image.new("RGBA", size, color + (0,))
    layer.putalpha(g)
    return layer


def ctext(d, cx, y, text, font, fill, stroke=0, sc=(0, 0, 0, 180), anchor="mm"):
    d.text((cx, y), text, font=font, fill=fill, anchor=anchor,
           stroke_width=stroke, stroke_fill=sc)


def wrap(d, text, font, maxw):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur); cur = ""; continue
        if d.textlength(cur + ch, font=font) <= maxw:
            cur += ch
        else:
            lines.append(cur); cur = ch
    lines.append(cur)
    return lines


def ensure():
    for d in (VIS,):
        os.makedirs(d, exist_ok=True)


# ----------------------------- 主海报（竖版 1080x1920） -----------------------------
def poster_vertical():
    W, H = 1080, 1920
    base = cover(Image.open(HERO_V).convert("RGB"), (W, H))
    img = base.convert("RGBA")
    img.alpha_composite(vgrad((W, H), 130, 0))             # 顶部压暗
    img.alpha_composite(vgrad((W, H), 0, 175))             # 底部压暗
    d = ImageDraw.Draw(img)
    cx = W // 2
    ctext(d, cx, 150, "原创 2D 微动漫 · 校园心理成长", f(FB, 34), (222, 233, 245, 235))
    ctext(d, cx, 300, TITLE, f(FT, 168), (255, 255, 255, 255), stroke=3, sc=(40, 60, 90, 200))
    ctext(d, cx, 420, EN, f(FB, 34), (170, 196, 220, 230))
    # 金色分隔线
    d.line([(cx - 260, 480), (cx + 260, 480)], fill=(240, 200, 144, 220), width=3)
    for i, ln in enumerate(wrap(d, TAG, f(FB, 44), W - 240)):
        ctext(d, cx, 560 + i * 62, ln, f(FB, 44), (240, 244, 250, 245), stroke=2, sc=(0, 0, 0, 120))
    # 底部信息
    ctext(d, cx, H - 150, "现实的我 · 理想中的我 · 我以为必须成为的我", f(FB, 36), (235, 240, 248, 240))
    ctext(d, cx, H - 96, "高一1班 · 朱明萱 · 片长 3′30″", f(FBD, 38), (255, 236, 200, 245))
    ctext(d, cx, H - 44, "自我差异理论 Self-Discrepancy Theory · Higgins 1987", f(FB, 26), (190, 205, 222, 220))
    p = os.path.join(VIS, "主海报-竖版.png")
    img.convert("RGB").save(p)
    print("poster:", p)


# ----------------------------- 横版主视觉 1920x1080 -----------------------------
def key_horizontal():
    W, H = 1920, 1080
    base = cover(Image.open(HERO_H).convert("RGB"), (W, H)).convert("RGBA")
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = Image.new("L", (W, 1))
    for x in range(W):
        t = x / (W - 1)
        g.putpixel((x, 0), int(210 * max(0, 1 - t / 0.55)))
    g = g.resize((W, H))
    scrim.putalpha(g)
    base.alpha_composite(scrim)
    d = ImageDraw.Draw(base)
    x0 = 120
    d.text((x0, 250), "原创 2D 微动漫 · 校园心理成长", font=f(FB, 36), fill=(210, 226, 245, 240))
    d.text((x0 - 8, 310), f"《{TITLE}》", font=f(FT, 150), fill=(255, 255, 255, 255),
           stroke_width=3, stroke_fill=(30, 50, 80, 200))
    d.text((x0, 470), EN, font=f(FB, 34), fill=(176, 200, 224, 235))
    d.line([(x0, 520), (x0 + 520, 520)], fill=(240, 200, 144, 230), width=3)
    for i, ln in enumerate(wrap(d, TAG, f(FB, 46), 780)):
        d.text((x0, 560 + i * 66), ln, font=f(FB, 46), fill=(238, 243, 250, 245),
               stroke_width=2, stroke_fill=(0, 0, 0, 110))
    d.text((x0, 800), CREDIT, font=f(FBD, 36), fill=(255, 236, 200, 245))
    d.text((x0, 866), TOOLS, font=f(FB, 24), fill=(200, 214, 230, 225))
    p = os.path.join(VIS, "主视觉-横版.png")
    base.convert("RGB").save(p)
    print("kv:", p)


# ----------------------------- 角色卡 ×3 -----------------------------
def char_cards():
    grp = Image.open(os.path.join(CHARS, "三人设定表.png")).convert("RGB")
    W, H = grp.size
    thirds = [(0, 0, int(W * 0.34), H), (int(W * 0.32), 0, int(W * 0.68), H), (int(W * 0.66), 0, W, H)]
    meta = [
        ("林一", "LIN YI", "现实自我 · 主人公", "那如果我今天不开心呢？", (91, 107, 124)),
        ("一林", "YI LIN", "理想 / 应该自我 · 完美倒影", "那就不要让他们看出来。", (127, 216, 255)),
        ("陈晓", "CHEN XIAO", "朋友 · 陪伴者", "那你不用在我面前装没事。", (242, 166, 90)),
    ]
    for (name, en, role, quote, accent), box in zip(meta, thirds):
        CW, CH = 900, 1500
        crop = grp.crop(box)
        bg = cover(crop, (CW, CH)).convert("RGBA")
        bg.alpha_composite(vgrad((CW, CH), 90, 210))
        d = ImageDraw.Draw(bg)
        cx = CW // 2
        # 顶部色条
        d.rectangle([0, 0, CW, 12], fill=accent + (255,))
        ctext(d, cx, 92, name, f(FT, 96), (255, 255, 255, 255), stroke=3, sc=(0, 0, 0, 130))
        ctext(d, cx, 168, en, f(FB, 30), (200, 216, 232, 235))
        d.line([(cx - 200, 216), (cx + 200, 216)], fill=accent + (230,), width=3)
        # 引言
        qy = CH - 300
        for i, ln in enumerate(wrap(d, f"“{quote}”", f(FB, 46), CW - 160)):
            ctext(d, cx, qy + i * 60, ln, f(FB, 46), (245, 248, 252, 250), stroke=2, sc=(0, 0, 0, 130))
        ctext(d, cx, CH - 150, role, f(FBD, 36), lighten(accent, 0.35) + (255,))
        ctext(d, cx, CH - 74, "《满分的我》 原创 2D 微动漫", f(FB, 28), (215, 226, 240, 230))
        p = os.path.join(VIS, f"角色卡-{name}.png")
        bg.convert("RGB").save(p)
        print("char:", p)


# ----------------------------- 剧照九宫格 1080x1080 -----------------------------
def nine_grid():
    names = ["S02-点赞特写", "S03-洗手间林一", "S04-试卷塞书包", "S08-完美九宫格",
             "S10-虚拟自我登场", "S11-明暗分屏", "S14-镜面包围", "S27-真实的笑", "S29-黄昏奔跑"]
    W = 1080; cell = (W - 4 * 24) // 3; top = 150
    H = top + 3 * cell + 4 * 24 + 70
    canvas = Image.new("RGB", (W, H), (245, 243, 238))
    d = ImageDraw.Draw(canvas)
    ctext(d, W // 2, 66, "《满分的我》 · 剧照九宫格", f(FT, 58), (40, 52, 70))
    ctext(d, W // 2, 112, "Original 2D Micro-Animation · Stills", f(FB, 24), (130, 140, 155))
    for i, nm in enumerate(names):
        r, c = divmod(i, 3)
        x = 24 + c * (cell + 24)
        y = top + r * (cell + 24)
        im = cover(Image.open(os.path.join(SHOTS, nm + ".png")).convert("RGB"), (cell, cell))
        canvas.paste(im, (x, y))
        d.rectangle([x, y, x + cell - 1, y + cell - 1], outline=(255, 255, 255), width=3)
    ctext(d, W // 2, H - 40, "高一1班 · 朱明萱 ｜ 校园心理成长 ｜ 片长 3′30″", f(FB, 28), (110, 120, 135))
    p = os.path.join(VIS, "剧照九宫格.png")
    canvas.save(p)
    print("grid:", p)


# ----------------------------- 展架 / 易拉宝 900x2200 -----------------------------
def rollup():
    W, H = 900, 2200
    imgh = int(W * 0.62)
    canvas = Image.new("RGB", (W, H), (18, 26, 40))
    bg = cover(Image.open(HERO_H).convert("RGB"), (W, imgh)).convert("RGBA")
    bg.alpha_composite(vgrad((W, imgh), 0, 205, (18, 26, 40)))
    canvas.paste(bg.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(canvas)
    cx = W // 2
    y = imgh + 70
    ctext(d, cx, y, TITLE, f(FT, 140), (255, 255, 255), stroke=3, sc=(40, 60, 90))
    ctext(d, cx, y + 110, EN, f(FB, 30), (170, 196, 220))
    d.line([(cx - 220, y + 165), (cx + 220, y + 165)], fill=(240, 200, 144), width=3)
    y += 210
    for ln in wrap(d, TAG, f(FB, 40), W - 120):
        ctext(d, cx, y, ln, f(FB, 40), (240, 244, 250)); y += 56
    y += 40
    for line in [
        "现实的我 · 理想中的我 · 我以为必须成为的我",
        "",
        "心理学知识点：自我差异理论（Self-Discrepancy Theory, Higgins 1987）",
        "你可以努力成为更好的自己，但不必先变得完美，才配得到认可。",
        "",
        "类别：微动漫（原创 2D 动画）",
        "班级 / 姓名：高一1班 · 朱明萱",
        "播放时长：约 3 分 30 秒",
        "制作：Qwen-Image-2.1 · ACE-Step · Qwen3-TTS · Krita · OpenToonz · Kdenlive · FFmpeg",
    ]:
        fnt = f(FB, 30)
        col = (232, 238, 246)
        if line.startswith("心理学") or line.startswith("你可以"):
            fnt = f(FBD, 32); col = (255, 236, 200)
        ctext(d, cx, y, line or " ", fnt, col); y += 50
    p = os.path.join(VIS, "展架-易拉宝.png")
    canvas.save(p)
    print("rollup:", p)


# ----------------------------- 作品信息卡 1080x1440 -----------------------------
def info_card():
    W, H = 1080, 1440
    base = cover(Image.open(HERO_H).convert("RGB"), (W, H)).convert("RGBA")
    base.alpha_composite(vgrad((W, H), 150, 210))
    d = ImageDraw.Draw(base)
    cx = W // 2
    ctext(d, cx, 80, "作品信息", f(FBD, 40), (255, 236, 200))
    ctext(d, cx, 190, TITLE, f(FT, 120), (255, 255, 255), stroke=3, sc=(0, 0, 0, 120))
    ctext(d, cx, 280, EN, f(FB, 28), (200, 216, 232))
    y = 380
    rows = [
        ("作品名称", "满分的我（The Perfect Me）"),
        ("作品类别", "微动漫 · 原创 2D 动画"),
        ("参赛信息", "高一1班 · 朱明萱"),
        ("题材类型", "校园心理 · 成长 · 原创 2D 动漫"),
        ("核心理论", "自我差异理论（Higgins, 1987）"),
        ("主要角色", "林一（现实自我）· 一林（理想/应该自我）· 陈晓（朋友）"),
        ("播放时长", "约 3 分 30 秒（≤5 分钟）"),
        ("文件格式", "MP4 / H.264 / AAC，≤200MB"),
        ("主题立意", "你可以努力成为更好的自己，但不必先变得完美，才配得到认可。"),
        ("原创声明", "角色、场景、台词、分镜、提示词均为原创；图像/配乐/配音由本地开源模型生成。"),
    ]
    for k, v in rows:
        d.text((90, y), k, font=f(FBD, 32), fill=(255, 236, 200))
        for i, ln in enumerate(wrap(d, v, f(FB, 30), W - 90 - 300)):
            d.text((330, y + i * 42), ln, font=f(FB, 30), fill=(236, 242, 249))
        y += 42 * max(1, len(wrap(d, v, f(FB, 30), W - 90 - 300))) + 26
    p = os.path.join(VIS, "作品信息卡.png")
    base.convert("RGB").save(p)
    print("info:", p)


def wechat_banner():
    W, H = 900, 383
    base = cover(Image.open(HERO_H).convert("RGB"), (W, H)).convert("RGBA")
    scrim = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = Image.new("L", (W, 1))
    for x in range(W):
        g.putpixel((x, 0), int(200 * max(0, 1 - (x / (W - 1)) / 0.6)))
    scrim.putalpha(g.resize((W, H)))
    base.alpha_composite(scrim)
    d = ImageDraw.Draw(base)
    d.text((46, 120), TITLE, font=f(FT, 96), fill=(255, 255, 255), stroke_width=3, stroke_fill=(30, 50, 80))
    d.text((50, 236), "原创 2D 微动漫 · 校园心理成长", font=f(FB, 30), fill=(226, 236, 248))
    d.text((50, 284), "高一1班 · 朱明萱 ｜ 片长 3′30″", font=f(FBD, 30), fill=(255, 236, 200))
    p = os.path.join(VIS, "公众号头图-900x383.png")
    base.convert("RGB").save(p)
    print("wechat:", p)


if __name__ == "__main__":
    ensure()
    poster_vertical()
    key_horizontal()
    char_cards()
    nine_grid()
    rollup()
    info_card()
    wechat_banner()
    print("done ->", VIS)
