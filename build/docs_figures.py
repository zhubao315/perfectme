#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》文档配图：为统一风格的插画加一致的下方信息条（编号 + 标题 + 副题）。

源图：本地 Qwen-Image-2.1 生成（images/，同一风格前缀）
输出：09-文档配图/*.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "images")
OUT = os.path.join(ROOT, "09-文档配图")
FT = "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc"
FB = "/usr/local/share/fonts/windows/msyh.ttc"
GOLD = (240, 200, 144)

FIGS = [
    ("20261010-201331-0.png", "00-总览-封面.png",        "DOC-00 · 项目总览",     "从剧本到成片的完整创作"),
    ("20261010-201347-0.png", "A-策划创作.png",           "DOC-A · 策划创作",      "剧本 · 分镜 · 逐镜动画"),
    ("20261010-201416-0.png", "B1-角色设定.png",          "DOC-B1 · 角色设定",     "三名原创角色"),
    ("20261010-201432-0.png", "B2-场景与提示词.png",      "DOC-B2 · 场景 · 提示词", "四个主要场景"),
    ("20261010-201453-0.png", "C1-原创配乐.png",          "DOC-C1 · 原创配乐",     "焦虑 → 冲突 → 释然"),
    ("20261010-201509-0.png", "C2-配音.png",              "DOC-C2 · 配音",         "三种原创音色"),
    ("20261010-201531-0.png", "D1-制作工程.png",          "DOC-D1 · 制作工程",     "从构思到成片"),
    ("20261010-201547-0.png", "E-宣传物料.png",           "DOC-E · 宣传物料",      "作品与展示"),
]


def f(p, s):
    try:
        return ImageFont.truetype(p, s, index=0)
    except Exception:
        return ImageFont.truetype(p, s)


def bar(img):
    W, H = img.size
    bh = int(H * 0.24)
    grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = Image.new("L", (1, H))
    for y in range(H):
        a = 0 if y < H - bh else int(190 * (y - (H - bh)) / bh)
        g.putpixel((0, y), a)
    grad.putalpha(g.resize((W, H)))
    img = Image.alpha_composite(img.convert("RGBA"), grad)
    d = ImageDraw.Draw(img)
    x, yb = int(W * 0.055), H - int(H * 0.09)
    d.line([(x, yb - 30), (x + 54, yb - 30)], fill=GOLD + (235,), width=4)
    d.text((x, yb - 12), FIGS_TITLE, font=f(FT, int(H * 0.052)), fill=(255, 255, 255, 255), anchor="ls")
    d.text((x, yb + 6), FIGS_SUB, font=f(FB, int(H * 0.032)), fill=(214, 226, 240, 240), anchor="ls")
    return img.convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    global FIGS_TITLE, FIGS_SUB
    for src, dst, title, sub in FIGS:
        FIGS_TITLE, FIGS_SUB = title, sub
        p = os.path.join(IMG, src)
        img = Image.open(p)
        img = bar(img)
        img.save(os.path.join(OUT, dst))
        print("figure:", dst, img.size)


if __name__ == "__main__":
    main()
