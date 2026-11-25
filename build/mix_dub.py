#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》配音版多轨混音与成片合成

轨道组织：
    V1  视频（OpenToonz 动画，含既有字幕/氛围叠加）
    A1  林一   A2  一林   A3  陈晓   A6  旁白
    A4  配乐（ACE-Step：焦虑 → 冲突 → 释然）
    A5  音效（手机提示音 / 镜面音效 / 操场环境声）

用法：python3 build/mix_dub.py
"""
import os, re, sys, subprocess, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene  # noqa
from tts_dub import LINES, OUT_DIR, SR  # noqa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
MULTI = os.path.join(ROOT, "05-音频", "多轨")
SFXDIR = os.path.join(BUILD, "sfx")
BGM = os.path.join(BUILD, "music.wav")
VIDEO_IN = os.path.join(ROOT, "07-成片", "满分的我.mp4")
VIDEO_OUT = os.path.join(ROOT, "07-成片", "满分的我(配音版).mp4")
MIX = os.path.join(BUILD, "mix.wav")


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD:", " ".join(cmd)); print(r.stderr[-3000:]); sys.exit(1)
    return r


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", p], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 0.0


def loudnorm_measure(p, target=-16.0, tp=-1.5, lra=11.0):
    """第一遍 loudnorm，返回测量 JSON（用于第二遍线性归一）。"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", p, "-af",
                        f"loudnorm=I={target}:TP={tp}:LRA={lra}:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr
    return json.loads(txt[txt.rfind("{"):txt.rfind("}") + 1])


def norm_to_mono(src, out):
    run(["ffmpeg", "-y", "-v", "error", "-i", src,
         "-ar", str(SR), "-ac", "1", out])


def build_stem(items, total, out):
    """items: [(wav, start_sec, gain?, window?)] -> 单条时间轴轨（静音铺底）。
    window>0 且 wav 超长时按 atempo 收紧（上限 1.5x）。"""
    if not items:
        run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
             f"anullsrc=r={SR}:cl=mono", "-t", f"{total:.3f}", out])
        return
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for it in items:
        cmd += ["-i", it[0]]
    fc = []
    for i, it in enumerate(items):
        wav, s = it[0], it[1]
        g = it[2] if len(it) > 2 else 1.0
        win = it[3] if len(it) > 3 else 0.0
        ms = int(round(s * 1000))
        af = ""
        if win:
            d = dur(wav)
            if d > win * 1.02:
                af = f",atempo={min(1.5, d / win):.3f}"
        fc.append(f"[{i}:a]adelay={ms}|{ms},volume={g}{af}[a{i}]")
    fc.append("".join(f"[a{i}]" for i in range(len(items))) +
              f"amix=inputs={len(items)}:normalize=0,apad[aout]")
    cmd += ["-filter_complex", ";".join(fc), "-map", "[aout]",
            "-t", f"{total:.3f}", "-ar", str(SR), "-ac", "1", out]
    run(cmd)


def line_files(who):
    """返回该角色的 (文件, 起始秒, gain, window) 列表（镜面声归入 一林）。"""
    starts = scene.load_starts()
    res = []
    for idx, (sid, off, win, w, text) in enumerate(scene.LINES, 1):
        ns = scene.line_start(sid, off, starts)
        if w == "镜面声":
            if who != "一林":
                continue
            for j in range(1, 4):
                p = os.path.join(OUT_DIR, f"V{idx:02d}_镜面声_{j}.wav")
                if os.path.exists(p):
                    res.append((p, ns + (j - 1) * 0.35, 1.0, 0.0))
        elif w == who:
            p = os.path.join(OUT_DIR, f"V{idx:02d}_{who}.wav")
            if os.path.exists(p):
                res.append((p, ns, 1.0, win))
    return res


def gen_sfx():
    """引用 build/sfx_gen.py 程序化合成的音效，按 scene.SFX 的镜号+偏移落位。

    返回 [(wav, start_sec, gain)]。若文件缺失会提示先运行 sfx_gen.py。
    """
    starts = scene.load_starts()
    missing = [n for (_, _, n, _) in scene.SFX
               if not os.path.exists(os.path.join(SFXDIR, n + ".wav"))]
    if missing:
        print("缺少音效文件（请先 python3 build/sfx_gen.py）:", missing)
    items = []
    for sid, off, name, gain in scene.SFX:
        items.append((os.path.join(SFXDIR, name + ".wav"),
                      scene.line_start(sid, off, starts), gain))
    return items


def main():
    os.makedirs(MULTI, exist_ok=True)
    T = dur(VIDEO_IN)
    print("视频时长 =", T)

    # ---- 对白分轨 ----
    stems = {}
    for role in ("林一", "一林", "陈晓", "旁白"):
        out = os.path.join(MULTI, f"A{ {'林一':1,'一林':2,'陈晓':3,'旁白':6}[role] }_{role}.wav")
        build_stem(line_files(role), T, out)
        stems[role] = out
        print("stem:", os.path.basename(out))

    # ---- 配乐 A4 ----
    a4 = os.path.join(MULTI, "A4_配乐.wav")
    norm_to_mono(BGM, a4)

    # ---- 音效 A5 ----
    a5 = os.path.join(MULTI, "A5_音效.wav")
    build_stem(gen_sfx(), T, a5)
    print("stem: A5_音效.wav")

    # ---- 混音：对白(A1+A2+A3+A6) 提升清晰度并强侧链压低配乐(A4)，叠加并突出音效(A5) ----
    # 先做静态响度归一（两遍），避免单遍 loudnorm 的动态抽吸破坏「对白/配乐」对比。
    fc = (
        "[0:a][1:a][2:a][3:a]amix=inputs=4:normalize=0,"
        "highpass=f=90,equalizer=f=3000:t=q:w=1.2:g=2,volume=2.1,"
        "asplit=2[dlg][dlg2];"
        "[4:a]volume=0.55[bgm];"
        "[bgm][dlg]sidechaincompress=threshold=0.05:ratio=20:attack=6:release=300[bd];"
        "[5:a]highpass=f=110,volume=1.2[sfx];"
        "[dlg2][bd][sfx]amix=inputs=3:normalize=0:weights='1.0 0.9 0.9',"
        "alimiter=limit=0.97[amixout]"
    )
    raw = os.path.join(BUILD, "mix_raw.wav")
    run(["ffmpeg", "-y", "-v", "error",
         "-i", stems["林一"], "-i", stems["一林"], "-i", stems["陈晓"], "-i", stems["旁白"],
         "-i", a4, "-i", a5,
         "-filter_complex", fc, "-map", "[amixout]",
         "-t", f"{T:.3f}", "-ar", "44100", "-ac", "2", raw])
    m = loudnorm_measure(raw)
    af = ("loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:"
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}")
    run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af,
         "-ar", "44100", "-ac", "2", MIX])
    print(f"mix: {MIX}  (loudnorm {m['input_i']} -> -16 LUFS, linear)")

    # ---- 合成成片：V1 + 新音轨 ----
    run(["ffmpeg", "-y", "-v", "error",
         "-i", VIDEO_IN, "-i", MIX,
         "-map", "0:v", "-map", "1:a",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", VIDEO_OUT])
    print("配音版成片:", VIDEO_OUT)


if __name__ == "__main__":
    main()
