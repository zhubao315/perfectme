#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从完整配音排程生成精确同步的 ASS 字幕（中文，关键词暖金渐变，淡入上浮）。"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, 'build')
PLAN = os.path.join(BUILD, 'mix_full_plan.json')
OUT = os.path.join(BUILD, 'subs_full.ass')
TOTAL = 243.3


def ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f'{h}:{m:02d}:{s:05.2f}'


def main():
    plan = json.load(open(PLAN, encoding='utf-8'))
    events = plan['events']
    lines = [
        '[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1920', 'PlayResY: 1080',
        'WrapStyle: 0', 'ScaledBorderAndShadow: yes', '',
        '[V4+ Styles]',
        'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
        'Style: Sub,Microsoft YaHei,46,&H00FFFFFF,&H0080C8F0,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,60,60,70,1',
        'Style: Narr,Microsoft YaHei,42,&H00F0E6D8,&H0080C8F0,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,2,2,60,60,70,1',
        '',
        '[Events]',
        'Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
    ]
    for wav, start, dur, who, text, sid in events:
        style = 'Narr' if who == '旁白' else 'Sub'
        end = min(start + dur + 0.35, TOTAL)
        # 关键词渐暖
        out = text
        for kw in ('真实', '接纳', '不完美', '成长', '满分', '努力'):
            out = out.replace(kw, '{\\c&HE6D8BC&}' + kw + '{\\c&HFFFFFF&}')
        tag = '{\\an2\\fad(300,300)\\move(960,1016,960,1002,0,600)}'
        lines.append(f'Dialogue: 0,{ts(start)},{ts(end)},{style},,0,0,0,,{tag}{out}')
    open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('wrote', OUT, len(events), 'lines')


if __name__ == '__main__':
    main()
