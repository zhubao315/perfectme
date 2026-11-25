#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 H3 片段按原时间轴拼接，套回原配音与字幕，生成动画版成片。"""
import importlib.util
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, "build")
CLIPS = os.path.join(BUILD, "h3_clips")
SEGS = os.path.join(BUILD, "h3_segments")
FINAL_SRC = os.path.join(ROOT, "07-成片", "满分的我(配音版).mp4")
SUBS = os.path.join(ROOT, "07-成片", "满分的我-字幕.ass")
OUT = os.path.join(ROOT, "07-成片", "满分的我-动画版-H3.mp4")
W, H, FPS = 1920, 1080, 25


def run(cmd):
    print("RUN", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def probe_duration(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", path], text=True).strip()
    return float(out)


def vf():
    return (f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p")


def main():
    os.makedirs(SEGS, exist_ok=True)
    spec = importlib.util.spec_from_file_location("scene", os.path.join(BUILD, "scene.py"))
    scene = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scene)
    starts = json.load(open(os.path.join(BUILD, "timeline.json"), encoding="utf-8"))
    ids = [s["id"] for s in scene.SHOTS]
    total_shots = sum(float(s["dur"]) for s in scene.SHOTS)
    credits_start = round(total_shots - len(ids) * scene.TR, 3)
    endcard_start = round(total_shots + 9.0 - (len(ids) + 1) * scene.TR, 3)
    total = probe_duration(FINAL_SRC)

    print(f"credits={credits_start}s endcard={endcard_start}s total={total:.2f}s", flush=True)
    segments = []
    for i, sid in enumerate(ids):
        start = float(starts[sid])
        end = float(starts[ids[i + 1]]) if i + 1 < len(ids) else credits_start
        dur = round(end - start, 3)
        seg = os.path.join(SEGS, f"{sid}.mp4")
        if sid in ("s01", "s32"):
            # 片名卡 / 主题句卡含文字，沿用原片，避免 H3 生成乱码
            run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", FINAL_SRC,
                 "-vf", vf(), "-an", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "20", "-r", str(FPS), seg])
        elif sid == "s02":
            run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={W}x{H}:r={FPS}",
                 "-t", f"{dur:.3f}", "-vf", "format=yuv420p", "-c:v", "libx264",
                 "-preset", "veryfast", "-crf", "20", seg])
        else:
            clip = os.path.join(CLIPS, sid + ".mp4")
            if not os.path.isfile(clip):
                raise FileNotFoundError(f"missing H3 clip: {clip}")
            run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", clip, "-t", f"{dur:.3f}",
                 "-vf", vf(), "-an", "-c:v", "libx264", "-preset", "veryfast",
                 "-crf", "20", "-r", str(FPS), seg])
        segments.append(seg)
        print(f"SEG {sid} {dur}s", flush=True)

    # 片尾滚动字幕 / 感谢观看卡沿用原片
    for name, start, end in (("credits", credits_start, endcard_start),
                             ("endcard", endcard_start, total)):
        seg = os.path.join(SEGS, name + ".mp4")
        run(["ffmpeg", "-y", "-ss", f"{start:.3f}", "-t", f"{end - start:.3f}",
             "-i", FINAL_SRC, "-vf", vf(), "-an", "-c:v", "libx264",
             "-preset", "veryfast", "-crf", "20", "-r", str(FPS), seg])
        segments.append(seg)
        print(f"SEG {name} {end - start:.3f}s", flush=True)

    lst = os.path.join(SEGS, "concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    joined = os.path.join(SEGS, "joined.mp4")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])

    sub_path = SUBS.replace("'", "\\'").replace(":", "\\:")
    run(["ffmpeg", "-y", "-i", joined, "-i", FINAL_SRC,
         "-vf", f"subtitles='{sub_path}'",
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", OUT])
    print("OUTPUT", OUT, os.path.getsize(OUT), flush=True)


if __name__ == "__main__":
    main()
