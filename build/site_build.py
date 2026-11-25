#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""宣传网站资源准备：把素材转成 web 友好格式，输出到 10-宣传网站/assets/。

用法：python3 build/site_build.py
"""
import os, shutil, subprocess
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "10-宣传网站")
A = os.path.join(SITE, "assets")
IMG = os.path.join(ROOT, "images")


def jpg(src, dst, w=None, q=82):
    im = Image.open(src).convert("RGB")
    if w and im.width > w:
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    im.save(os.path.join(A, dst), "JPEG", quality=q, optimize=True, progressive=True)
    print("img", dst, im.size)


def cp(src, dst):
    shutil.copy2(src, os.path.join(A, dst))
    print("cp ", dst, f"{os.path.getsize(src)//1024}KB")


def mp3(src, dst):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-b:a", "128k",
                    os.path.join(A, dst)], check=True)
    print("mp3", dst)


def main():
    os.makedirs(A, exist_ok=True)
    jpg(f"{IMG}/20261010-200406-0.png", "hero-wide.jpg", 1920)
    jpg(f"{IMG}/20261010-200445-0.png", "hero-tall.jpg", 1100)
    jpg(f"{IMG}/20261010-202033-0.png", "char-linyi.jpg", 900)
    jpg(f"{IMG}/20261010-202049-0.png", "char-yilin.jpg", 900)
    jpg(f"{IMG}/20261010-202105-0.png", "char-chenxiao.jpg", 900)
    jpg(f"{ROOT}/08-宣传物料/01-主视觉/主海报-竖版.png", "poster.jpg", 1080)
    jpg(f"{ROOT}/08-宣传物料/01-主视觉/主视觉-横版.png", "kv.jpg", 1600)
    stills = ["S02-点赞特写", "S03-洗手间林一", "S04-试卷塞书包", "S08-完美九宫格",
              "S10-虚拟自我登场", "S11-明暗分屏", "S14-镜面包围", "S22-暖色光点",
              "S27-真实的笑", "S29-黄昏奔跑", "S32-片尾定格"]
    for i, s in enumerate(stills, 1):
        p = f"{ROOT}/04-分镜图/镜头/{s}.png"
        if os.path.exists(p):
            jpg(p, f"still-{i:02d}.jpg", 1500)
    cp(f"{ROOT}/08-宣传物料/03-预告片/满分的我-预告片.mp4", "trailer.mp4")
    cp(f"{ROOT}/07-成片/满分的我-动画版-H3.mp4", "film.mp4")
    for name, dst in [("林一", "voice-linyi"), ("一林", "voice-yilin"),
                      ("陈晓", "voice-chenxiao"), ("旁白", "voice-narrator")]:
        mp3(f"{ROOT}/05-音频/配音/试音/{name}.wav", dst + ".mp3")
    print("done ->", A)


if __name__ == "__main__":
    main()
