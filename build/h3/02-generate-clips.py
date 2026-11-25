#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用本地 MiniMax-H3 图生视频逐镜生成《满分的我》动画片段。

复用 mov2 已验证的扁平 ComfyUI API 图；单卡容器 18201，8 步 turbo。
"""
import argparse
import json
import os
import shutil
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, "build")
H3 = os.path.join(BUILD, "h3")
COMFY = os.environ.get("COMFYUI_URL", "http://127.0.0.1:18201")
INPUT_DIR = "/data/comfyui-minimax-h3/input"
OUTPUT_DIR = "/data/comfyui-minimax-h3/output"
MANIFEST = os.path.join(BUILD, "h3_manifest.json")
TEMPLATE = os.path.join(H3, "api-prompt-template.json")
CLIPS = os.path.join(BUILD, "h3_clips")
LOG = os.path.join(BUILD, "h3_generate_log.json")
WIDTH, HEIGHT = 960, 544

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def api(path, payload=None, timeout=30):
    data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    req = urllib.request.Request(COMFY + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with opener.open(req, timeout=timeout) as resp:
        return json.load(resp)


def prepare_image(src, name):
    from PIL import Image
    im = Image.open(src).convert("RGB")
    ratio = WIDTH / HEIGHT
    w, h = im.size
    if w / h > ratio:
        nw = int(h * ratio)
        im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    else:
        nh = int(w / ratio)
        im = im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    im = im.resize((WIDTH, HEIGHT), Image.LANCZOS)
    dst = os.path.join(INPUT_DIR, name)
    im.save(dst)
    return dst


def make_prompt(shot, first_name, last_name):
    p = json.load(open(TEMPLATE, encoding="utf-8"))
    p["901"] = {"class_type": "LoadImage", "inputs": {"image": first_name}}
    p["139"]["inputs"].update({
        "prompt": shot["prompt"],
        "width": WIDTH,
        "height": HEIGHT,
        "length": shot["length"],
        "first_frame": ["901", 0],
    })
    if last_name:
        p["902"] = {"class_type": "LoadImage", "inputs": {"image": last_name}}
        p["139"]["inputs"]["last_frame"] = ["902", 0]
    p["137"]["inputs"]["noise_seed"] = shot["seed"]
    p["900"]["inputs"]["filename_prefix"] = "video/pmf_" + shot["shot_id"]
    return p


def wait_job(pid, timeout=1800):
    deadline = time.time() + timeout
    while time.time() < deadline:
        entry = api("/history/" + pid).get(pid)
        if entry:
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(json.dumps(status, ensure_ascii=False)[:3000])
            if status.get("completed"):
                return entry.get("outputs", {})
        time.sleep(10)
    raise TimeoutError(pid)


def find_video(outputs):
    for value in outputs.values():
        for key in ("gifs", "images", "videos"):
            for item in value.get(key, []):
                filename = item.get("filename", "")
                if filename.lower().endswith((".mp4", ".webm", ".mov")):
                    return os.path.join(OUTPUT_DIR, item.get("subfolder", ""), filename)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", nargs="*", help="shot ids, e.g. s03 s04")
    ap.add_argument("--limit", type=int, help="generate first N shots only")
    ap.add_argument("--force", action="store_true", help="regenerate shots marked done")
    args = ap.parse_args()

    shots = json.load(open(MANIFEST, encoding="utf-8"))
    if args.shots:
        shots = [s for s in shots if s["shot_id"] in args.shots]
    if args.limit:
        shots = shots[:args.limit]
    os.makedirs(CLIPS, exist_ok=True)
    log = json.load(open(LOG, encoding="utf-8")) if os.path.isfile(LOG) else {}

    for shot in shots:
        sid = shot["shot_id"]
        if log.get(sid, {}).get("status") == "done" and not args.force:
            print(f"SKIP {sid} (already done)", flush=True)
            continue
        first = f"pmf_{sid}.png"
        last = f"pmf_{sid}_last.png" if shot.get("src2") else None
        prepare_image(os.path.join(ROOT, "04-分镜图", shot["src"]), first)
        if last:
            prepare_image(os.path.join(ROOT, "04-分镜图", shot["src2"]), last)
        prompt = make_prompt(shot, first, last)
        print(f"START {sid} len={shot['length']} last_frame={bool(last)}", flush=True)
        try:
            pid = api("/prompt", {"prompt": prompt, "front": True})["prompt_id"]
            outputs = wait_job(pid)
            video = find_video(outputs)
            if not video:
                raise RuntimeError("no video in outputs: " + json.dumps(outputs, ensure_ascii=False)[:1000])
            dst = os.path.join(CLIPS, sid + ".mp4")
            shutil.copy2(video, dst)
            log[sid] = {"status": "done", "pid": pid, "file": dst,
                        "prompt": shot["prompt"], "length": shot["length"],
                        "seed": shot["seed"]}
            print(f"DONE {sid} -> {dst}", flush=True)
        except Exception as ex:
            log[sid] = {"status": "error", "error": str(ex)[:2000]}
            print(f"ERROR {sid}: {ex}", flush=True)
        with open(LOG, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    print("ALL FINISHED", flush=True)


if __name__ == "__main__":
    main()
