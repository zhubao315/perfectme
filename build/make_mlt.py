#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据已生成的片段生成可编辑工程文件（MLT，可被 Kdenlive / Shotcut 打开）"""
import os, glob, subprocess, json

ROOT = "/oc/mov"
BUILD = os.path.join(ROOT, "build")
CLIPS = os.path.join(BUILD, "clips")
OUTDIR = os.path.join(ROOT, "06-工程源文件")
FPS = 25
W, H = 1920, 1080

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())

def tc(f):
    h = f // (3600 * FPS); m = (f // (60 * FPS)) % 60
    s = (f // FPS) % 60; fr = f % FPS
    return f"{h:02d}:{m:02d}:{s:02d}.{fr:02d}"

seg = os.path.join(BUILD, "segments.txt")
if os.path.exists(seg):
    clips = [l.strip() for l in open(seg, encoding="utf-8") if l.strip()]
else:
    clips = sorted(glob.glob(os.path.join(CLIPS, "*.mp4")))
music = os.path.join(BUILD, "music.wav")
subs = os.path.join(BUILD, "subs.ass")

prods, vpl = [], []
total = 0
for i, c in enumerate(clips):
    n = int(round(dur(c) * FPS))
    prods.append(f'''  <producer id="v{i}">
    <property name="mlt_service">avformat</property>
    <property name="resource">{c}</property>
    <property name="length">{n}</property>
    <property name="set.test_image">1</property>
  </producer>''')
    vpl.append(f'    <entry producer="v{i}" in="0" out="{n-1}"/>')
    total += n

mtotal = int(round(dur(music) * FPS))
prods.append(f'''  <producer id="music">
    <property name="mlt_service">avformat</property>
    <property name="resource">{music}</property>
    <property name="length">{mtotal}</property>
  </producer>''')

xml = f'''<?xml version="1.0" encoding="utf-8"?>
<mlt LC_NUMERIC="C" version="7.22.0" title="满分的我" producer="main_bin">
  <profile description="HD 1080p 25 fps" width="{W}" height="{H}" progressive="1" sample_aspect_num="1" sample_aspect_den="1" display_aspect_num="16" display_aspect_den="9" frame_rate_num="{FPS}" frame_rate_den="1" colorspace="709"/>
{chr(10).join(prods)}
  <playlist id="videoplay">{chr(10)}{chr(10).join(vpl)}
  </playlist>
  <playlist id="audioplay">
    <entry producer="music" in="0" out="{total-1}"/>
  </playlist>
  <tractor id="maintractor" title="满分的我" global_feed="1">
    <property name="kdenlive:projectTractor">1</property>
    <track producer="videoplay"/>
    <track producer="audioplay"/>
    <transition id="mix0">
      <property name="mlt_service">mix</property>
      <property name="internal_added">237</property>
      <property name="always_active">1</property>
      <property name="sum">1</property>
      <property name="a_track">0</property>
      <property name="b_track">1</property>
    </transition>
    <filter id="subtitle0">
      <property name="mlt_service">avfilter.subtitles</property>
      <property name="av.filename">{subs}</property>
      <property name="disable">0</property>
    </filter>
  </tractor>
  <tractor id="main_bin" title="项目素材箱">
    <property name="kdenlive:docproperties.version">1.04</property>
    <property name="kdenlive:docproperties.guidesCategories">[]</property>
    <track producer="maintractor"/>
  </tractor>
</mlt>
'''

os.makedirs(OUTDIR, exist_ok=True)
dst = os.path.join(OUTDIR, "满分的我-工程.mlt")
with open(dst, "w", encoding="utf-8") as f:
    f.write(xml)
print("工程文件:", dst, "总帧数:", total, f"({total/FPS:.1f}s)")
