#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""《满分的我》A5 音效生成（纯 Python 程序化合成，无第三方素材）

覆盖音效清单：手机提示音、心跳、纸页摩擦、快门、笔尖/秒针、像素上浮、
玻璃嗡鸣/回声、声音抽空、水滴、笔迹浮现、操场环境声。

输出：build/sfx/*.wav（24kHz 单声道）
用法：python3 build/sfx_gen.py
"""
import math, os, random, wave

SR = 24000
SFXDIR = "/oc/mov/build/sfx"
random.seed(20261010)


# --------------------------- 基础 DSP ---------------------------
def silence(n):
    return [0.0] * n


def norm(data, peak=0.9):
    m = max((abs(x) for x in data), default=0.0)
    if m < 1e-9:
        return data
    k = peak / m
    return [x * k for x in data]


def write_wav(path, data, peak=0.9):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = norm(data, peak)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(b"".join(int(max(-1, min(1, x)) * 32767).to_bytes(2, "little", signed=True) for x in d))


def white(n):
    return [random.uniform(-1, 1) for _ in range(n)]


def brown(n, leak=0.02):
    out = []; last = 0.0
    for _ in range(n):
        last += leak * random.uniform(-1, 1)
        if last > 1: last = 1.0
        elif last < -1: last = -1.0
        out.append(last)
    return out


def lp1(data, fc):
    a = 1 - math.exp(-2 * math.pi * fc / SR)
    y = 0.0; out = []
    for x in data:
        y += a * (x - y); out.append(y)
    return out


def hp1(data, fc):
    a = math.exp(-2 * math.pi * fc / SR)
    y = 0.0; xp = 0.0; out = []
    for x in data:
        y = a * (y + x - xp); xp = x; out.append(y)
    return out


def echo(data, d_s, fb):
    d = int(d_s * SR); out = [0.0] * len(data)
    for i, x in enumerate(data):
        out[i] = x + (fb * out[i - d] if i >= d else 0.0)
    return out


def tremolo(data, f, depth):
    return [x * (1 - depth * (0.5 + 0.5 * math.sin(2 * math.pi * f * i / SR)))
            for i, x in enumerate(data)]


def fade(data, fin=0.0, fout=0.0):
    n = len(data)
    for i in range(n):
        g = 1.0
        if fin and i < fin * SR:
            g *= i / (fin * SR)
        if fout and i > n - fout * SR:
            g *= max(0.0, (n - i) / (fout * SR))
        data[i] *= g
    return data


def add(dst, src, at_s, gain=1.0):
    off = int(at_s * SR)
    for i, s in enumerate(src):
        j = off + i
        if 0 <= j < len(dst):
            dst[j] += s * gain


def bell(f0, dur, amp=1.0, partials=((1, 1.0, 0.45), (2.0, 0.5, 0.30),
                                     (3.01, 0.25, 0.20), (4.16, 0.13, 0.13))):
    n = int(dur * SR); out = silence(n)
    for ratio, a2, tau in partials:
        f = f0 * ratio
        for i in range(n):
            t = i / SR
            out[i] += amp * a2 * math.sin(2 * math.pi * f * t) * math.exp(-t / tau)
    return out


# --------------------------- 各音效 ---------------------------
def sfx_notification(soft=False):
    dur = 1.0; out = silence(int(dur * SR))
    add(out, bell(1174.66, 0.9, 0.9), 0.0)
    add(out, bell(1567.98, 0.8, 0.85), 0.10)
    if soft:
        out = lp1(out, 6000)
        return [x * 0.6 for x in out]
    return out


def sfx_heartbeat():
    dur = 1.3; out = silence(int(dur * SR))
    def thump(at, amp):
        n = int(0.5 * SR)
        for i in range(n):
            t = i / SR
            env = math.exp(-t / 0.055)
            s = math.sin(2 * math.pi * 52 * t) + 0.5 * math.sin(2 * math.pi * 104 * t)
            j = int(at * SR) + i
            if j < len(out):
                out[j] += amp * env * s
    thump(0.0, 1.0); thump(0.30, 0.75)
    return lp1(out, 220)


def sfx_paper():
    dur = 0.55; n = int(dur * SR)
    nz = hp1(lp1(white(n), 6000), 900)
    out = []
    for i in range(n):
        t = i / SR
        bumps = sum(math.exp(-((t - c) ** 2) / (2 * 0.05 ** 2)) for c in (0.06, 0.18, 0.30, 0.44))
        out.append(nz[i] * (0.25 + bumps))
    return out


def sfx_shutter():
    dur = 0.28; out = silence(int(dur * SR))
    def click(at, amp, fc):
        n = int(0.05 * SR)
        nz = hp1(lp1(white(n), 12000), fc)
        for i in range(n):
            out[int(at * SR) + i] += amp * nz[i] * math.exp(-(i / SR) / 0.006)
    click(0.0, 1.0, 2500)
    click(0.055, 0.7, 4000)
    return out


def sfx_pen():
    dur = 2.2; n = int(dur * SR)
    scratch = hp1(lp1(white(n), 7000), 1800)
    out = []
    for i in range(n):
        t = i / SR
        env = 0.35 + 0.5 * abs(math.sin(2 * math.pi * 1.3 * t)) * math.exp(-t / 2.0)
        out.append(scratch[i] * env * 0.5)
    for k in range(4):  # 秒针节拍
        add(out, bell(2200, 0.12, 0.5, ((1, 1.0, 0.03), (2.4, 0.4, 0.02))), 0.15 + k * 0.5)
    return out


def sfx_pixel_rise():
    dur = 0.7; n = int(dur * SR); out = silence(n)
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = 380 + 1250 * (t / dur)
        ph += 2 * math.pi * f / SR
        env = math.exp(-((t - dur * 0.55) ** 2) / (2 * (dur * 0.28) ** 2))
        out[i] = 0.6 * math.sin(ph) * env + 0.25 * math.sin(2 * ph) * env
    shimmer = hp1(lp1(white(n), 9000), 4000)
    for i in range(n):
        out[i] += 0.12 * shimmer[i] * math.exp(-((i / SR - dur * 0.55) ** 2) / (2 * (dur * 0.28) ** 2))
    return out


def sfx_glass(dur=6.0):
    n = int(dur * SR); out = silence(n)
    for f, a in ((1810, 0.5), (2687, 0.3), (3355, 0.2), (720, 0.25)):
        ph = 0.0
        for i in range(n):
            ph += 2 * math.pi * f / SR
            out[i] += a * math.sin(ph)
    out = tremolo(out, 0.7, 0.5)
    nz = hp1(white(n), 4500)
    for i in range(n):
        out[i] += 0.10 * nz[i]
    out = echo(out, 0.28, 0.5)
    return fade(out, 1.5, 1.8)


def sfx_vacuum():
    dur = 0.9; n = int(dur * SR)
    nz = white(n); out = []
    y = 0.0
    for i in range(n):
        t = i / SR
        fc = 6000 * (1 - t / dur) + 300
        a = 1 - math.exp(-2 * math.pi * fc / SR)
        y += a * (nz[i] - y)
        env = math.sin(math.pi * t / dur) ** 2 * (1 - t / dur)
        out.append(y * env)
    return out


def sfx_drop():
    dur = 0.5; out = silence(int(dur * SR))
    def one(at, amp):
        n = int(0.35 * SR); ph = 0.0
        for i in range(n):
            t = i / SR
            f = 360 + 1500 * (1 - math.exp(-t / 0.02))
            ph += 2 * math.pi * f / SR
            env = (1 - math.exp(-t / 0.004)) * math.exp(-t / 0.05)
            j = int(at * SR) + i
            if j < len(out):
                out[j] += amp * math.sin(ph) * env
    one(0.0, 1.0); one(0.18, 0.4)
    return out


def sfx_appear():
    dur = 0.9; n = int(dur * SR); out = silence(n)
    ph = 0.0
    for i in range(n):
        t = i / SR
        f = 1600 - 900 * math.sin(math.pi * min(t / dur, 1.0))
        ph += 2 * math.pi * f / SR
        env = math.exp(-((t - dur * 0.5) ** 2) / (2 * (dur * 0.3) ** 2))
        out[i] = 0.35 * math.sin(ph) * env
    nz = hp1(lp1(white(n), 8000), 3000)
    for i in range(n):
        out[i] += 0.10 * nz[i] * math.exp(-((i / SR - dur * 0.5) ** 2) / (2 * (dur * 0.3) ** 2))
    return out


def sfx_playground(dur=42.0):
    n = int(dur * SR)
    bed = lp1(brown(n), 1100)
    bed = [x * 0.5 for x in bed]
    # 远处人声般的稀疏"交谈"团
    chatter = hp1(lp1(white(n), 2600), 350)
    out = [0.0] * n
    for i in range(n):
        t = i / SR
        slow = 0.5 + 0.5 * math.sin(2 * math.pi * 0.13 * t + 1.0)
        burst = max(0.0, math.sin(2 * math.pi * 0.21 * t + 0.5)) ** 6
        out[i] = bed[i] + 0.10 * chatter[i] * (0.3 + 0.7 * burst) * slow
    # 远处铃铛/笑语点缀
    for at in (3.5, 9.0, 14.5, 21.0, 27.5, 33.0, 38.0):
        add(out, bell(880 + random.uniform(-80, 120), 0.7, 0.12,
                      ((1, 1.0, 0.15), (2.0, 0.4, 0.10))), at)
    return fade(out, 4.0, 5.0)


FILES = {
    "notif": sfx_notification(),
    "notif_soft": sfx_notification(soft=True),
    "heartbeat": sfx_heartbeat(),
    "paper": sfx_paper(),
    "shutter": sfx_shutter(),
    "pen": sfx_pen(),
    "pixel": sfx_pixel_rise(),
    "glass": sfx_glass(6.0),
    "glass2": sfx_glass(4.0),
    "vacuum": sfx_vacuum(),
    "drop": sfx_drop(),
    "appear": sfx_appear(),
    "playground": sfx_playground(42.0),
    "playground_end": sfx_playground(14.0),
}


def main():
    for name, data in FILES.items():
        p = os.path.join(SFXDIR, name + ".wav")
        write_wav(p, data)
        print(f"{name:16s} {len(data)/SR:6.2f}s -> {p}")


if __name__ == "__main__":
    main()
