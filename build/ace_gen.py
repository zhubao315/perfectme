#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用本地 ACE-Step v1（ComfyUI @ 127.0.0.1:18190）生成《满分的我》三段原创配乐。
纯器乐（lyrics=[inst]），无 vocals/歌词。
"""
import json, os, time, urllib.request

BASE = os.environ.get("ACE_BASE", "http://127.0.0.1:18190")
CKPT = "ace_step_v1_3.5b.safetensors"
OUT_DIR = "/oc/mov/build/ace_output"

TRACKS = [
    dict(
        name="opening",
        seconds=82.0, seed=2026101001,
        tags=("cinematic instrumental, psychological suspense, modern campus drama, "
              "sparse piano notes, low sub-bass electronic ambience, soft phone "
              "notification blips, slow pulse rhythm, restrained, minimal, spacious, "
              "building quiet tension, cold, introspective, no vocals"),
    ),
    dict(
        name="conflict",
        seconds=82.0, seed=2026101002,
        tags=("cinematic instrumental, dark psychological drama, low frequency pulsing bass, "
              "sustained low string drone, slowly swelling strings, subtle dissonance, "
              "rising tension turning to clarity, sudden silence then a gentle single piano "
              "note, restrained, no vocals"),
    ),
    dict(
        name="ending",
        seconds=82.0, seed=2026101003,
        tags=("warm cinematic instrumental, soft piano, light airy strings, gentle ambient pad, "
              "slow soothing tempo, hopeful and sincere, sunset campus, acceptance friendship "
              "hope, warm but not overly sentimental, natural fade out, no vocals"),
    ),
]


def graph(tags, seconds, seed, prefix):
    return {
        "40": {"class_type": "CheckpointLoaderSimple",
               "inputs": {"ckpt_name": CKPT}},
        "51": {"class_type": "ModelSamplingSD3",
               "inputs": {"model": ["40", 0], "shift": 5.0}},
        "14": {"class_type": "TextEncodeAceStepAudio",
               "inputs": {"clip": ["40", 1], "tags": tags,
                          "lyrics": "[inst]", "lyrics_strength": 1.0}},
        "44": {"class_type": "ConditioningZeroOut",
               "inputs": {"conditioning": ["14", 0]}},
        "17": {"class_type": "EmptyAceStepLatentAudio",
               "inputs": {"seconds": seconds, "batch_size": 1}},
        "52": {"class_type": "KSampler",
               "inputs": {"model": ["51", 0], "positive": ["14", 0], "negative": ["44", 0],
                          "latent_image": ["17", 0], "seed": seed, "steps": 50,
                          "cfg": 5.0, "sampler_name": "euler", "scheduler": "simple",
                          "denoise": 1.0}},
        "18": {"class_type": "VAEDecodeAudio",
               "inputs": {"samples": ["52", 0], "vae": ["40", 2]}},
        "60": {"class_type": "SaveAudio",
               "inputs": {"audio": ["18", 0], "filename_prefix": f"ace/{prefix}"}},
    }


def submit(g):
    data = json.dumps({"prompt": g}).encode()
    req = urllib.request.Request(BASE + "/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=60).read())
    if "prompt_id" not in resp:
        raise RuntimeError(json.dumps(resp, ensure_ascii=False)[:800])
    return resp["prompt_id"]


def wait(pid, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(4)
        hist = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}", timeout=30).read())
        if pid not in hist:
            continue
        h = hist[pid]
        st = h.get("status", {})
        if st.get("status_str") == "error":
            raise RuntimeError(json.dumps(st.get("messages", []), ensure_ascii=False)[:2000])
        out = []
        for _n, o in h.get("outputs", {}).items():
            for key in ("audio", "images", "gifs", "files"):
                for a in o.get(key, []):
                    sub = a.get("subfolder", "")
                    out.append(os.path.join(OUT_DIR, sub, a["filename"]))
        if out:
            return out
    raise TimeoutError(f"{pid} timeout")


for t in TRACKS:
    g = graph(t["tags"], t["seconds"], t["seed"], t["name"])
    print(f"[ACE] submit {t['name']} ({t['seconds']}s, seed {t['seed']}) ...", flush=True)
    pid = submit(g)
    t0 = time.time()
    files = wait(pid)
    print(f"[ACE] {t['name']} done in {time.time()-t0:.0f}s -> {files}", flush=True)
