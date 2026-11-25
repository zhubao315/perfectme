#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成《满分的我》配音版 Kdenlive 工程（V1 + A1–A3 + A4 配乐 + A5 音效 + A6 旁白）

基于 06-工程源文件/满分的我-工程.mlt 的视频剪辑序列，追加多轨音频。
输出：06-工程源文件/满分的我-配音版.mlt
"""
import os, re, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "06-工程源文件", "满分的我-工程.mlt")
DST = os.path.join(ROOT, "06-工程源文件", "满分的我-配音版.mlt")
MULTI = os.path.join(ROOT, "05-音频", "多轨")
FPS = 25

AUDIO = [
    ("A1", "a_linyi",   os.path.join(MULTI, "A1_林一.wav")),
    ("A2", "a_yilin",   os.path.join(MULTI, "A2_一林.wav")),
    ("A3", "a_chenxiao",os.path.join(MULTI, "A3_陈晓.wav")),
    ("A4", "a_bgm",     os.path.join(MULTI, "A4_配乐.wav")),
    ("A5", "a_sfx",     os.path.join(MULTI, "A5_音效.wav")),
    ("A6", "a_narr",    os.path.join(MULTI, "A6_旁白.wav")),
]


def dur(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nk=1:nw=1", p], capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    src = open(SRC, encoding="utf-8").read()

    # 1) 视频 producer / playlist（原样复用）
    vid_producers = re.findall(r'  <producer id="v\d+">.*?</producer>\n', src, re.S)
    video_playlist = re.search(r'  <playlist id="videoplay">.*?</playlist>\n', src, re.S).group(0)

    # 2) 音频 producer
    aud_prod = ""
    for _, pid, path in AUDIO:
        length = int(round(dur(path) * FPS))
        aud_prod += (f'  <producer id="{pid}">\n'
                     f'    <property name="mlt_service">avformat</property>\n'
                     f'    <property name="resource">{path}</property>\n'
                     f'    <property name="length">{length}</property>\n'
                     f'  </producer>\n')

    # 3) 音频 playlist
    aud_play = ""
    for name, pid, path in AUDIO:
        length = int(round(dur(path) * FPS))
        aud_play += (f'  <playlist id="{name}">\n'
                     f'    <entry producer="{pid}" in="0" out="{length-1}"/>\n'
                     f'  </playlist>\n')

    # 4) 主 tractor：V1 + A1..A6，逐轨 mix 汇总
    tracks = '    <track producer="videoplay"/>\n'
    mixes = ""
    for i, (name, _, _) in enumerate(AUDIO, start=1):
        tracks += f'    <track producer="{name}"/>\n'
        mixes += ('    <transition id="mix%d">\n'
                  '      <property name="mlt_service">mix</property>\n'
                  '      <property name="always_active">1</property>\n'
                  '      <property name="sum">1</property>\n'
                  '      <property name="a_track">0</property>\n'
                  '      <property name="b_track">%d</property>\n'
                  '    </transition>\n' % (i, i))

    mlt = f'''<?xml version="1.0" encoding="utf-8"?>
<mlt LC_NUMERIC="C" version="7.22.0" title="满分的我(配音版)" producer="main_bin">
  <profile description="HD 1080p 25 fps" width="1920" height="1080" progressive="1" sample_aspect_num="1" sample_aspect_den="1" display_aspect_num="16" display_aspect_den="9" frame_rate_num="25" frame_rate_den="1" colorspace="709"/>
{vid_producers}{aud_prod}{video_playlist}{aud_play}  <tractor id="maintractor" title="满分的我(配音版)" global_feed="1">
    <property name="kdenlive:projectTractor">1</property>
{tracks}{mixes}    <filter id="subtitle0">
      <property name="mlt_service">avfilter.subtitles</property>
      <property name="av.filename">/oc/mov/build/subs.ass</property>
      <property name="disable">0</property>
    </filter>
  </tractor>
  <tractor id="main_bin" title="项目素材箱">
    <property name="kdenlive:docproperties.version">1.04</property>
    <track producer="maintractor"/>
  </tractor>
</mlt>
'''
    with open(DST, "w", encoding="utf-8") as f:
        f.write(mlt)

    # 校验 XML
    import xml.dom.minidom as md
    md.parse(DST)
    print("written & valid XML:", DST)


if __name__ == "__main__":
    main()
