#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加长版混音：对白/音效按 SCALE 缩放后的时间轴重排，BGM 循环铺满，响度归一到 -16 LUFS。"""
import json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene
import mix_dub as M

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
OUT = os.path.join(BUILD, 'mix_long.wav')
MULTI = os.path.join(BUILD, 'h3_long_audio')
SCALE = float(os.environ.get('H3_SCALE', '1.6'))
T = float(os.environ.get('H3_TOTAL', '243.0'))

_orig_load_starts = scene.load_starts

def scaled_starts():
    return {k: v * SCALE for k, v in _orig_load_starts().items()}

scene.load_starts = scaled_starts


def loop_bgm(src, out, total):
    M.run(['ffmpeg', '-y', '-v', 'error', '-stream_loop', '-1', '-i', src,
           '-t', f'{total:.3f}', '-ar', str(M.SR), '-ac', '1', out])


def main():
    os.makedirs(MULTI, exist_ok=True)
    print(f'SCALE={SCALE} TOTAL={T:.2f}s', flush=True)
    stems = {}
    for role in ('林一', '一林', '陈晓', '旁白'):
        out = os.path.join(MULTI, f'A_{role}.wav')
        M.build_stem(M.line_files(role), T, out)
        stems[role] = out
        print('stem:', role, flush=True)

    a4 = os.path.join(MULTI, 'BGM_loop.wav')
    loop_bgm(M.BGM, a4, T)
    a5 = os.path.join(MULTI, 'SFX.wav')
    M.build_stem(M.gen_sfx(), T, a5)
    print('stem: SFX', flush=True)

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
    raw = os.path.join(BUILD, 'mix_long_raw.wav')
    M.run(['ffmpeg', '-y', '-v', 'error',
           '-i', stems['林一'], '-i', stems['一林'], '-i', stems['陈晓'], '-i', stems['旁白'],
           '-i', a4, '-i', a5, '-filter_complex', fc, '-map', '[amixout]',
           '-t', f'{T:.3f}', '-ar', '44100', '-ac', '2', raw])
    m = M.loudnorm_measure(raw)
    af = ('loudnorm=I=-16:TP=-1.5:LRA=11:linear=true:'
          f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
          f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}")
    M.run(['ffmpeg', '-y', '-v', 'error', '-i', raw, '-af', af, '-ar', '44100', '-ac', '2', OUT])
    print('mix:', OUT, json.dumps(m), flush=True)


if __name__ == '__main__':
    main()
