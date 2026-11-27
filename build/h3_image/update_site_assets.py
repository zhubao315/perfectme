#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用新生成的分镜图刷新网站剧照，并把最终加长版成片复制到站点 assets。"""
import os, shutil
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
A = os.path.join(ROOT, '10-宣传网站', 'assets')
SHOTS = os.path.join(ROOT, '04-分镜图', '镜头')
STILLS = ['S02-点赞特写', 'S03-洗手间林一', 'S04-试卷塞书包', 'S08-完美九宫格',
          'S10-虚拟自我登场', 'S11-明暗分屏', 'S14-镜面包围', 'S22-暖色光点',
          'S27-真实的笑', 'S29-黄昏奔跑', 'S32-片尾定格']
FILM = os.path.join(ROOT, '07-成片', '满分的我-动画版-H3-加长版.mp4')


def main():
    for i, name in enumerate(STILLS, 1):
        src = os.path.join(SHOTS, name + '.png')
        if not os.path.isfile(src):
            print('MISSING', src); continue
        im = Image.open(src).convert('RGB')
        im.thumbnail((1500, 1500), Image.LANCZOS)
        dst = os.path.join(A, f'still-{i:02d}.jpg')
        im.save(dst, 'JPEG', quality=85, optimize=True, progressive=True)
        print('jpg', os.path.basename(dst), im.size)
    # 主角卡用新生成的角色主形象
    src = os.path.join(ROOT, '04-分镜图', '角色', '林一-主形象.png')
    if os.path.isfile(src):
        im = Image.open(src).convert('RGB')
        im.thumbnail((900, 900), Image.LANCZOS)
        im.save(os.path.join(A, 'char-linyi.jpg'), 'JPEG', quality=85, optimize=True, progressive=True)
    if os.path.isfile(FILM):
        shutil.copy2(FILM, os.path.join(A, 'film.mp4'))
        print('film ->', os.path.join(A, 'film.mp4'))
    else:
        print('film not ready yet:', FILM)


if __name__ == '__main__':
    main()
