#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 build/scene.py（单一事实源）生成 H3 逐镜任务清单。"""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, "build")
IMG = os.path.join(ROOT, "04-分镜图")
OUT = os.path.join(BUILD, "h3_manifest.json")

LENGTHS = [73, 90, 107, 124, 141, 158, 175, 192, 204]
STYLE = ("轻薄半赛璐淡彩动漫风格，细腻纸纹，柔和空气感，"
         "慢、轻、柔的局部动态，人物造型与服装保持一致，"
         "无字幕，无文字，无水印。")
MOTION = {"in": "镜头极缓慢推近。", "pan": "镜头极缓慢横移。", "hold": "画面几乎静止，只有极轻微呼吸感。"}

# 每镜画面/动作提示词（对应 scene.py 的 src，按逐镜动画分镜表描述）
PROMPTS = {
    "s03": "手机屏幕上不断跳出点赞通知，指尖轻轻滑动，屏幕冷光映在脸上。",
    "s04": "少年独自坐在洗手间隔间里低头看手机，笑容慢慢消失，肩膀微微垂下。",
    "s05": "把试卷塞进书包，拉链缓慢拉上，手指停顿。",
    "s06": "少年对着镜子练习微笑，嘴角勉强上扬，眼神却没有笑意。",
    "s07": "深夜书桌前低头写作业，笔尖移动，台灯暖光轻晃。",
    "s08": "手机相册里的完美九宫格自拍，画面轻微滑动，光斑缓缓闪动。",
    "s09": "空荡荡的教室，窗外树影轻轻晃动，阳光缓慢移动。",
    "s10": "半透明的虚拟自我在光中浮现，发丝与衣角轻轻飘动。",
    "s11": "少年抬头望向虚影，虚拟自我缓缓低头回应。",
    "s12": "画面明暗分屏，两侧光影缓慢流动，两人隔着光对视。",
    "s13": "虚拟自我轻声劝说，淡色光点在空气中缓慢漂浮。",
    "s14": "四面透明镜面包围少年，镜中的完美影像微微晃动。",
    "s15": "少年捂住耳朵，眉头紧皱，表情越来越痛苦。",
    "s16": "虚拟自我沉默下来，身上的光晕缓慢减弱。",
    "s17": "指尖缓缓触碰镜面，涟漪般的光纹向四周扩散。",
    "s18": "镜面中出现三个重叠的自我影像，缓缓错开。",
    "s19": "淡彩示意图式的三个自我轮廓，柔和光晕缓缓流转。",
    "s20": "少年独自站在自我差异示意图前，眼神低垂，光色逐渐变暖。",
    "s21": "暖色光点缓缓升起，少年嘴角慢慢浮现释然的微笑。",
    "s22": "暖光中两人安静对视，光点漂浮，气氛柔和。",
    "s23": "放学后的教室，窗边光影移动，课桌安静空着。",
    "s24": "朋友伸出手，少年犹豫后抬眼，手慢慢抬起。",
    "s25": "朋友温和注视，少年低头倾诉，暖光落在肩上。",
    "s26": "少年露出真实的笑容，笑意渐渐加深，眼睛慢慢发亮。",
    "s27": "两人并肩走着，回头相视，夕阳把影子拉长。",
    "s28": "黄昏操场上奔跑的身影，衣角与发丝随风飘动。",
    "s29": "深夜书桌上手机屏幕慢慢暗下，台灯余光轻晃。",
    "s30": "少年慢慢放下手机，屏幕光熄灭，神情渐渐平静。",
    "s31": "少年望向远方，暖色空气光点缓慢漂浮。",
}


def pick_length(duration):
    target = max(3.0, min(float(duration), 8.5)) * 24
    return min(LENGTHS, key=lambda x: abs(x - target))


def main():
    spec = importlib.util.spec_from_file_location("scene", os.path.join(BUILD, "scene.py"))
    scene = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene)
    starts, _ = scene.compute()

    manifest = []
    for shot in scene.SHOTS:
        sid, src = shot["id"], shot["src"]
        if src.startswith("#"):
            print(f"SKIP {sid}: special card {src}")
            continue
        if sid not in PROMPTS:
            print(f"SKIP {sid}: no prompt defined")
            continue
        src2 = shot.get("src2")
        prompt = STYLE + MOTION.get(shot["motion"], "") + PROMPTS[sid]
        if src2:
            prompt += "结尾自然过渡到另一表情或姿势，保持同一人物与服装。"
        manifest.append({
            "shot_id": sid,
            "src": src,
            "src2": src2,
            "start": round(starts[sid], 3),
            "duration": shot["dur"],
            "motion": shot["motion"],
            "length": pick_length(shot["dur"]),
            "seed": 2000 + int(sid[1:]),
            "prompt": prompt,
        })

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"WROTE {OUT}: {len(manifest)} shots")


if __name__ == "__main__":
    main()
