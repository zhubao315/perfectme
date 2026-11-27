#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整配音混音：每句用自然时长，不做 atempo 压缩；后续台词顺延避免重叠。

由于 TTS 旧 key 失效，复用已生成的 26 条配音文件，按台词自然时长重新排程，
生成加长版（H3_SCALE 时间轴）完整音轨。长句完整播放，镜头停留时间加长以容纳。
"""
import json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene
import mix_dub as M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
OUT = os.path.join(BUILD, 'mix_full.wav')
VOICES = os.path.join(ROOT, '05-音频', '配音')
MULTI = os.path.join(BUILD, 'h3_full_audio')
SCALE = float(os.environ.get('H3_SCALE', '1.6'))

# 时间轴：按镜起点错位排布；每句起始=max(原起点, 上一句结束+0.25)，保证零重叠且完整
GAP = 0.25


def plan():
    starts = {k: v * SCALE for k, v in scene.load_starts().items()}
    events = []
    cursor = {}
    for idx, (sid, off, win, who, text) in enumerate(scene.LINES, 1):
        wav = os.path.join(VOICES, f'V{idx:02d}_{who}.wav')
        if who == '镜面声':
            wav = os.path.join(VOICES, f'V{idx:02d}_镜面声_1.wav')
        if not os.path.isfile(wav):
            print('MISSING', wav); continue
        d = M.dur(wav)
        nominal = starts.get(sid, 0) + off * SCALE
        earliest = cursor.get(sid, 0)
        start = max(nominal, earliest)
        end = start + d + GAP
        cursor[sid] = end
        events.append((wav, start, d, who, text, sid))
    return events


def build_stem(events, who, total, out):
    items = [(e[0], e[1], 1.0, 0.0) for e in events if e[3] == who or (who == '一林' and e[3] == '镜面声')]
    M.build_stem(items, total, out)


def main():
    os.makedirs(MULTI, exist_ok=True)
    events = plan()
    total = max(e[1] + e[2] for e in events) + 6.0
    print(f'events={len(events)} total={total:.2f}s', flush=True)
    for e in events:
        print(f'  {e[5]} {e[3]:3s} start={e[1]:7.2f} dur={e[2]:5.2f} {e[4][:24]}', flush=True)
    stems = {}
    for role in ('林一', '一林', '陈晓', '旁白'):
        out = os.path.join(MULTI, f'full_{role}.wav')
        build_stem(events, role, total, out)
        stems[role] = out
    a4 = os.path.join(MULTI, 'bgm.wav')
    M.run(['ffmpeg', '-y', '-v', 'error', '-stream_loop', '-1', '-i', M.BGM,
           '-t', f'{total:.3f}', '-ar', str(M.SR), '-ac', '1', a4])
    a5 = os.path.join(MULTI, 'sfx.wav')
    # 去掉全部程序化音效（含刺啦/电流/玻璃摩擦声），只保留对白 + BGM
    M.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
           f'anullsrc=r={M.SR}:cl=mono', '-t', f'{total:.3f}', a5])

    fc = (
        '[0:a][1:a][2:a][3:a]amix=inputs=4:normalize=0,'
        'highpass=f=90,equalizer=f=3000:t=q:w=1.2:g=2,volume=2.1,'
        'asplit=2[dlg][dlg2];'
        '[4:a]volume=0.55[bgm];'
        '[bgm][dlg]sidechaincompress=threshold=0.05:ratio=20:attack=6:release=300[bd];'
        '[5:a]highpass=f=110,volume=1.2[sfx];'
        '[dlg2][bd][sfx]amix=inputs=3:normalize=0:weights=\'1.0 0.9 0.9\','
        'alimiter=limit=0.97[amixout]'
    )
    raw = os.path.join(BUILD, 'mix_full_raw.wav')
    M.run(['ffmpeg', '-y', '-v', 'error',
           '-i', stems['林一'], '-i', stems['一林'], '-i', stems['陈晓'], '-i', stems['旁白'],
           '-i', a4, '-i', a5, '-filter_complex', fc, '-map', '[amixout]',
           '-t', f'{total:.3f}', '-ar', '44100', '-ac', '2', raw])
    m = M.loudnorm_measure(raw)
    af = ('loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:'
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}")
    M.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', af, '-ar', '44100', '-ac', '2', OUT])
    json.dump({'total': total, 'events': events}, open(os.path.join(BUILD, 'mix_full_plan.json'), 'w'),
              ensure_ascii=False, indent=2)
    print('OUT', OUT, flush=True)


if __name__ == '__main__':
    main()
