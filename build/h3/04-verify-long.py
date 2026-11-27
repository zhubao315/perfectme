#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""加长版成片核验：时长/流信息/抽帧/字幕时间范围。"""
import json, os, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO = os.path.join(ROOT, '07-成片', '满分的我-动画版-H3-加长版.mp4')


def probe():
    out = subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries',
        'format=duration,size,bit_rate:stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_frames',
        '-of', 'json', VIDEO], text=True)
    return json.loads(out)


def main():
    info = probe()
    print(json.dumps(info, ensure_ascii=False, indent=2))
    for t in (20, 80, 150, 220):
        dst = f'/tmp/pmf_long_{t}.png'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', str(t), '-i', VIDEO,
                        '-frames:v', '1', dst], check=True)
        print('frame', t, dst, os.path.getsize(dst))


if __name__ == '__main__':
    main()
