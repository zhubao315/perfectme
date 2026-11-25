#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》配音生成脚本 · Qwen3-TTS (VoiceDesign)

- 通过本机 GPUStack 网关的 Qwen3-TTS-12Hz-1.7B-VoiceDesign 生成对白
- 逐句生成 05-音频/配音/Vxx_角色.wav，再用 ffmpeg 按时间轴合成 build/voice.wav
- 三个角色 + 旁白，音色由自然语言指令（VoiceDesign）设计

用法：
    python3 build/tts_dub.py            # 生成全部台词 + 合成整轨
    python3 build/tts_dub.py audition   # 只生成四条音色试听
"""
import os, re, sys, json, time, subprocess
import urllib.request
import array

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "05-音频", "配音")
AUD_DIR = os.path.join(OUT_DIR, "试音")
TRACK = os.path.join(ROOT, "build", "voice.wav")
SR = 24000

GW = "http://127.0.0.1:808/v1/audio/speech"
MODEL = "Qwen3-TTS-VoiceDesign-copy"
KEY = "gpustack_9457874f60c914a3_21cd849a76727db0ce8c243e3760dd05"

VOICES = {
    "林一":  "17岁中国高中男生，清亮的中音，声音自然，略带疲惫，敏感克制，情绪细腻，"
             "普通话标准，语速稍慢，像在压抑地自述",
    "一林":  "17岁中国高中男生，音色清晰、稳定、冷静，吐字利落，语气笃定，带一点距离感，"
             "干净的少年播音腔，不要机械电子音",
    "陈晓":  "17岁中国高中女生，音色温暖明亮、中性偏暖，语气自然随和，轻松生活化，"
             "像真实同学在聊天，亲切不煽情，吐字清晰",
    "旁白":  "成熟稳重的男声播音员旁白，字正腔圆，语速平稳，温和有磁性，叙述克制、无评判",
}
MIRROR = "一林叠声，压低音量、气声低语，克制中带压迫感，像许多个自己在耳边重复"

# (镜号, 镜内偏移秒, 时长上限秒, 说话人, 文本) —— 见 build/scene.py
LINES = scene.LINES


def to_new(t):
    """兼容旧接口：新时间轴已由 scene 直接给出，此处按镜号解析。"""
    starts = scene.load_starts()
    for sid, off, win, who, text in LINES:
        if abs(starts.get(sid, 0) + off - t) < 0.001:
            return starts[sid] + off
    return t


def synth(text, instructions, speed=1.0):
    body = {"model": MODEL, "input": text, "instructions": instructions,
            "task_type": "VoiceDesign", "language": "Auto",
            "response_format": "wav", "speed": speed}
    req = urllib.request.Request(
        GW, method="POST", data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"})
    last = None
    for attempt in range(4):
        try:
            data = urllib.request.urlopen(req, timeout=180).read()
            if data[:4] == b"RIFF":
                return data
            raise RuntimeError("non-wav: " + data[:200].decode("utf-8", "ignore"))
        except Exception as e:  # noqa
            last = e; time.sleep(2 + attempt * 3)
    raise RuntimeError(f"TTS failed: {last}")


def write_wav(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def dur_of(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def make_audition():
    os.makedirs(AUD_DIR, exist_ok=True)
    demo = {
        "林一": "又是一天。他们说，我过得真好。可我真的有点累了。",
        "一林": "你只需要再努力一点。别让大家失望，好吗？",
        "陈晓": "走啊，一起去操场？今天不聊成绩。",
        "旁白": "每个真实的瞬间，都被剪成了一张完美的照片。",
    }
    for name, text in demo.items():
        for attempt in range(3):
            try:
                write_wav(os.path.join(AUD_DIR, f"{name}.wav"), synth(text, VOICES[name]))
                print("audition ok:", name); break
            except Exception as e:
                print("audition retry", name, e); time.sleep(3)


def build_track(items, total):
    """items: list of (wav_path, start_seconds, window_seconds). 用 ffmpeg adelay+atempo+amix 合成整轨。
    window>0 且 wav 超长时，按 atempo 收紧（上限 1.5x，避免明显变调）。"""
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for it in items:
        cmd += ["-i", it[0]]
    fc = []
    for i, it in enumerate(items):
        s = it[1]
        win = it[2] if len(it) > 2 else 0.0
        ms = int(round(s * 1000))
        d = dur_of(it[0])
        af = ""
        if win and d > win * 1.02:
            tempo = min(1.5, d / win)
            af = f",atempo={tempo:.3f}"
        fc.append(f"[{i}:a]adelay={ms}|{ms},volume=1.0{af}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(items))) +
              f"amix=inputs={len(items)}:normalize=0,alimiter=limit=0.95,apad[aout]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[aout]", "-t", f"{total:.3f}",
            "-ar", str(SR), "-ac", "1", TRACK]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("ffmpeg err:\n", r.stderr[-3000:]); sys.exit(1)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    if len(sys.argv) > 1 and sys.argv[1] == "audition":
        make_audition(); return

    only = None
    if len(sys.argv) > 2 and sys.argv[1] == "only":
        only = sys.argv[2]

    starts = scene.load_starts()
    items, manifest = [], []
    for idx, (sid, off, win, who, text) in enumerate(LINES, 1):
        ns = scene.line_start(sid, off, starts)
        if only and who != only and who != "镜面声":
            continue
        if only and only != "一林" and who == "镜面声":
            continue
        if who == "镜面声":
            for j, p in enumerate([x.strip() for x in re.split("／|/", text) if x.strip()]):
                try:
                    data = synth(p, MIRROR, speed=0.95)
                except Exception as e:
                    print("FAIL", idx, who, e); continue
                name = f"V{idx:02d}_镜面声_{j+1}.wav"
                path = os.path.join(OUT_DIR, name)
                write_wav(path, data)
                items.append((path, ns + j * 0.35, 0.0))
            print(f"  V{idx:02d} 镜面声 ok (x3 叠声)")
        else:
            try:
                data = synth(text.replace("／", "。"), VOICES[who])
            except Exception as e:
                print("FAIL", idx, who, e); continue
            name = f"V{idx:02d}_{who}.wav"
            path = os.path.join(OUT_DIR, name)
            write_wav(path, data)
            items.append((path, ns, win))
            d = dur_of(path)
            manifest.append({"id": f"V{idx:02d}", "shot": sid, "speaker": who, "text": text,
                             "start": ns, "file": name, "dur": round(d, 2),
                             "window": win, "overflow": round(d - win, 2)})
            print(f"  V{idx:02d} {who} ok  {d:.2f}s / {win:.1f}s")

    if only:
        print(f"\n[only={only}] 已重新生成 {len(manifest)} 句，未改动整轨/manifest")
        for m in manifest:
            print(f'{m["id"]} {m["speaker"]} {m["dur"]}s / {m["window"]}s')
        return

    total = max(s for _, s, *_ in items) + 8.0
    build_track(items, total)

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print("\n=== 时长对照（overflow>0 表示超出配额的秒数，可能需要调速/精简） ===")
    for m in manifest:
        flag = "  <== OVER" if m["overflow"] > 0.15 else ""
        print(f'{m["id"]} {m["speaker"]:<4} {m["dur"]:>5.2f}s / {m["window"]:>4.1f}s ({m["overflow"]:+.2f}){flag}')
    print(f"\ntrack: {TRACK}  ~{total:.1f}s")


if __name__ == "__main__":
    main()
