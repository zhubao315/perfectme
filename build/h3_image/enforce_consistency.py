#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""人物一致性：用 Qwen-Image /images/edits 双图参考重生成所有含人物镜头。

第 1 个 image = 当前分镜图（保构图/场景），第 2 个 image = 角色主形象（锁长相）。
角色：林一（含一林变体）、陈晓。场景镜/特写镜跳过。
"""
import json, os, time, urllib.request, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, '04-分镜图')
LOG = os.path.join(ROOT, 'build', 'h3_image', 'consistency_log.json')
API = os.environ.get('QWEN_IMAGE_API', 'http://127.0.0.1:18189/v1')
TIMEOUT = 900

# 角色参考图（相对 ASSETS）
REF = {
    '林一': '角色/林一-主形象.png',
    '一林': '角色/三人设定表.png',   # 三人表中间角色为一林
    '陈晓': '角色/三人设定表.png',
}
# 含人物镜头 -> 主角色
CHAR_SHOTS = {
    'S03-洗手间林一.png': '林一', 'S03b-洗手间-更消沉.png': '林一',
    'S04-试卷塞书包.png': '林一',
    'S06-练习笑容.png': '林一', 'S06b-假笑.png': '林一',
    'S07-深夜写作业.png': '林一',
    'S10-虚拟自我登场.png': '一林', 'S10b-抬头看虚影.png': '一林',
    'S11-明暗分屏.png': '林一',
    'S14-镜面包围.png': '林一',
    'S15-捂耳朵.png': '林一', 'S15b-更痛苦.png': '林一',
    'S17-触碰镜面.png': '林一',
    'S22-暖色光点.png': '林一', 'S22b-释然微笑.png': '林一',
    'S26-陈晓伸手.png': '陈晓', 'S26b-伸手动作.png': '陈晓',
    'S27-真实的笑.png': '林一', 'S27b-笑更盛.png': '林一',
    'S29-黄昏奔跑.png': '林一',
    'S31-放下手机.png': '林一', 'S31b-放下手机.png': '林一',
    'S32-片尾定格.png': '林一',
}
DESC = {
    '林一': '15岁中国男高中生林一，圆脸、圆润杏眼、黑色短碎发、深蓝色水手领校服，眼神略疲惫',
    '一林': '虚拟自我一林，与林一同脸但头发一丝不乱、皮肤通透、眼中有高光、青蓝色柔光描边、左胸发光满环',
    '陈晓': '15岁中国女高中生陈晓，齐肩黑发扎低马尾、脸型偏圆、眉毛浓、橙色发圈',
}


def edit(target, ref, prompt):
    boundary = uuid.uuid4().hex
    chunks = []
    for k, v in {'model': 'qwen-image-2.1', 'prompt': prompt, 'steps': 8}.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for f in (target, ref):
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="image[]"; '
                       f'filename="{os.path.basename(f)}"\r\nContent-Type: image/png\r\n\r\n').encode())
        with open(f, 'rb') as fp:
            chunks.append(fp.read())
        chunks.append(b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    req = urllib.request.Request(API + '/images/edits', data=b''.join(chunks),
                                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    import base64
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        out = json.load(r)
    return base64.b64decode(out['data'][0]['b64_json'])


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--only', nargs='*')
    a = ap.parse_args()
    log = json.load(open(LOG, encoding='utf-8')) if os.path.isfile(LOG) else {}
    for name, role in CHAR_SHOTS.items():
        if a.only and name not in a.only:
            continue
        rel = '镜头/' + name
        if log.get(rel, {}).get('status') == 'done' and not a.force:
            continue
        target = os.path.join(ASSETS, rel)
        ref = os.path.join(ASSETS, REF[role])
        prompt = (f'保持第一张图的构图、场景和景别不变。人物严格参考第二张图的角色长相与服装：'
                  f'{DESC[role]}。画面干净，无文字，无水印，16:9。')
        t0 = time.time()
        try:
            blob = edit(target, ref, prompt)
            with open(target, 'wb') as f:
                f.write(blob)
            log[rel] = {'status': 'done', 'role': role, 'seconds': round(time.time()-t0,1)}
            print(f'DONE {name} ({role}, {log[rel]["seconds"]}s)', flush=True)
        except Exception as e:
            log[rel] = {'status': 'error', 'error': str(e)[:500]}
            print('ERROR', name, e, flush=True)
        json.dump(log, open(LOG, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('ALL FINISHED', flush=True)


if __name__ == '__main__':
    main()
