#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加长版合成：按 SCALE 缩放时间轴拼接 H3 长片段，烧录缩放后的字幕，套加长版混音。"""
import importlib.util, json, os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, 'build')
CLIPS = os.path.join(BUILD, 'h3_clips_qwen')
SEGS = os.path.join(BUILD, 'h3_segments_qwen')
FINAL_SRC = os.path.join(ROOT, '07-成片', '满分的我-动画版-H3-加长版.mp4')
SUBS = os.path.join(ROOT, '07-成片', '满分的我-字幕.ass')
SUBS_LONG = os.path.join(BUILD, 'subs_full.ass')
MIX = os.path.join(BUILD, 'mix_full.wav')
OUT = os.path.join(ROOT, '07-成片', '满分的我-动画版-H3-加长版.mp4')
W, H, FPS = 1920, 1080, 25
SCALE = float(os.environ.get('H3_SCALE', '1.6'))


def run(cmd):
    print('RUN', ' '.join(cmd), flush=True)
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def vf():
    return (f'scale={W}:{H}:force_original_aspect_ratio=increase,'
            f'crop={W}:{H},fps={FPS},setsar=1,format=yuv420p')


def ts_to_sec(t):
    h, m, s = t.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)


def sec_to_ts(x):
    h = int(x // 3600); m = int((x % 3600) // 60); s = x % 60
    return f'{h}:{m:02d}:{s:05.2f}'


def scale_ass():
    lines = []
    for line in open(SUBS, encoding='utf-8'):
        if line.startswith('Dialogue:'):
            parts = line.split(',', 3)
            parts[1] = sec_to_ts(ts_to_sec(parts[1]) * SCALE)
            parts[2] = sec_to_ts(ts_to_sec(parts[2]) * SCALE)
            line = ','.join(parts)
        lines.append(line)
    with open(SUBS_LONG, 'w', encoding='utf-8') as f:
        f.writelines(lines)


def main():
    spec = importlib.util.spec_from_file_location('scene', os.path.join(BUILD, 'scene.py'))
    scene = importlib.util.module_from_spec(spec); spec.loader.exec_module(scene)
    starts = json.load(open(os.path.join(BUILD, 'timeline.json'), encoding='utf-8'))
    ids = [s['id'] for s in scene.SHOTS]
    total_shots = sum(float(s['dur']) for s in scene.SHOTS)
    credits = round(total_shots - len(ids) * scene.TR, 3)
    endcard = round(total_shots + 9.0 - (len(ids) + 1) * scene.TR, 3)
    total = credits + (endcard - credits) + (0.0 - 0.0)  # 仅用于日志
    total *= SCALE
    print(f'credits={credits}SCALE={credits*SCALE:.2f}s endcard={endcard*SCALE:.2f}s total≈{total:.2f}s', flush=True)

    os.makedirs(SEGS, exist_ok=True)
    segments = []
    for i, sid in enumerate(ids):
        start = float(starts[sid]) * SCALE
        end = (float(starts[ids[i + 1]]) * SCALE) if i + 1 < len(ids) else credits * SCALE
        dur = round(end - start, 3)
        seg = os.path.join(SEGS, f'{sid}.mp4')
        if sid in ('s01', 's32'):
            original_start = float(starts[sid])
            run(['ffmpeg', '-y', '-ss', f'{original_start:.3f}', '-t', f'{dur:.3f}',
                 '-i', FINAL_SRC, '-vf', vf(), '-an', '-c:v', 'libx264',
                 '-preset', 'veryfast', '-crf', '20', '-r', str(FPS), seg])
        elif sid == 's02':
            run(['ffmpeg', '-y', '-f', 'lavfi', '-i', f'color=c=black:s={W}x{H}:r={FPS}',
                 '-t', f'{dur:.3f}', '-vf', 'format=yuv420p', '-c:v', 'libx264',
                 '-preset', 'veryfast', '-crf', '20', seg])
        else:
            clip = os.path.join(CLIPS, sid + '.mp4')
            if not os.path.isfile(clip):
                raise FileNotFoundError(clip)
            run(['ffmpeg', '-y', '-stream_loop', '-1', '-i', clip, '-t', f'{dur:.3f}',
                 '-vf', vf(), '-an', '-c:v', 'libx264', '-preset', 'veryfast',
                 '-crf', '20', '-r', str(FPS), seg])
        segments.append(seg)
        print(f'SEG {sid} {dur}s', flush=True)

    for name, a, b in (('credits', credits * SCALE, endcard * SCALE),
                       ('endcard', endcard * SCALE, endcard * SCALE + 9.0 * SCALE)):
        seg = os.path.join(SEGS, name + '.mp4')
        # 必须从原片用「原始时间点」提取；缩放后的时间会越过原片末尾导致空片段
        src_start = a / SCALE
        src_dur = (b - a) / SCALE
        tmp = os.path.join(SEGS, name + '_src.mp4')
        run(['ffmpeg', '-y', '-ss', f'{src_start:.3f}', '-t', f'{src_dur:.3f}',
             '-i', FINAL_SRC, '-vf', vf(), '-an', '-c:v', 'libx264',
             '-preset', 'veryfast', '-crf', '20', tmp])
        run(['ffmpeg', '-y', '-stream_loop', '-1', '-i', tmp, '-t', f'{b-a:.3f}',
             '-c', 'copy', seg])
        segments.append(seg)

    lst = os.path.join(SEGS, 'concat.txt')
    with open(lst, 'w') as f:
        for s in segments:
            f.write(f"file '{s}'\n")
    joined = os.path.join(SEGS, 'joined.mp4')
    run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', joined])

    # 字幕已由 make_subs_full.py 按完整配音排程精确生成，无需再缩放
    sub_path = SUBS_LONG.replace("'", "\\'").replace(':', '\\:')
    run(['ffmpeg', '-y', '-i', joined, '-i', MIX,
         '-vf', f"subtitles='{sub_path}'", '-map', '0:v:0', '-map', '1:a:0',
         '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
         '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
         '-movflags', '+faststart', '-shortest', OUT])
    print('OUTPUT', OUT, os.path.getsize(OUT), flush=True)


if __name__ == '__main__':
    main()
