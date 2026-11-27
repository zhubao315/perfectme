#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 minimax-h3-image（OpenAI 兼容 API）重新生成《满分的我》全部图片。

铁律：6 步/CFG=1 由服务端固定；无 negative_prompt（排除项已写进正面提示词）；
size 上限 2048×2048，这里用 2048×1152（16:9）；单张可能 5–7 分钟，超时 1200 秒。
变体图（Sxxb）走 /images/edits，第 1 个 image 是主图，保证同机位同构图。
"""
import argparse, base64, json, mimetypes, os, time, urllib.request, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, 'build', 'h3_image')
PROMPTS = os.path.join(BUILD, 'prompts.json')
LOG = os.path.join(BUILD, 'generate_log.json')
ASSETS = os.path.join(ROOT, '04-分镜图')
BACKUP = os.path.join(BUILD, 'original_backup')
API = os.environ.get('H3_IMAGE_API', 'http://192.168.1.3:18199/v1')
MODEL = 'minimax-h3-image'
SIZE = os.environ.get('H3_IMAGE_SIZE', '2048x1152')
TIMEOUT = 1200
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post_json(path, payload):
    req = urllib.request.Request(API + path, data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={'Content-Type': 'application/json'})
    with OPENER.open(req, timeout=TIMEOUT) as r:
        return json.load(r)


def post_multipart(path, fields, files):
    boundary = uuid.uuid4().hex
    chunks = []
    for k, v in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for field, filepath in files:
        ctype = mimetypes.guess_type(filepath)[0] or 'image/png'
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; '
                       f'filename="{os.path.basename(filepath)}"\r\nContent-Type: {ctype}\r\n\r\n').encode())
        with open(filepath, 'rb') as f:
            chunks.append(f.read())
        chunks.append(b'\r\n')
    chunks.append(f'--{boundary}--\r\n'.encode())
    req = urllib.request.Request(API + path, data=b''.join(chunks),
                                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    with OPENER.open(req, timeout=TIMEOUT) as r:
        return json.load(r)


def save_result(result, dest):
    data = result.get('data') or []
    if not data:
        raise RuntimeError('empty response: ' + json.dumps(result, ensure_ascii=False)[:500])
    item = data[0]
    if 'b64_json' in item:
        blob = base64.b64decode(item['b64_json'])
    elif item.get('url'):
        with OPENER.open(item['url'], timeout=120) as r:
            blob = r.read()
    else:
        raise RuntimeError('no image payload: ' + json.dumps(item)[:300])
    if not blob.startswith(b'\x89PNG') and not blob.startswith(b'\xff\xd8'):
        raise RuntimeError('not an image payload')
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'wb') as f:
        f.write(blob)
    return len(blob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*', help='specific asset paths, e.g. 镜头/S02-点赞特写.png')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--size', default=SIZE)
    args = ap.parse_args()

    items = json.load(open(PROMPTS, encoding='utf-8'))
    if args.only:
        items = [i for i in items if i['path'] in args.only]
    if args.limit:
        items = items[:args.limit]
    log = json.load(open(LOG, encoding='utf-8')) if os.path.isfile(LOG) else {}

    for item in items:
        rel = item['path']
        dest = os.path.join(ASSETS, rel)
        if log.get(rel, {}).get('status') == 'done' and not args.force:
            print(f'SKIP {rel}', flush=True); continue
        # 首次运行备份原图（git 也已跟踪，双保险）
        backup = os.path.join(BACKUP, rel)
        if os.path.isfile(dest) and not os.path.isfile(backup):
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            with open(dest, 'rb') as s, open(backup, 'wb') as d:
                d.write(s.read())
        started = time.time()
        try:
            if item['mode'] == 'edit':
                base_img = os.path.join(ASSETS, item['base_image'])
                if not os.path.isfile(base_img):
                    raise FileNotFoundError(base_img)
                result = post_multipart('/images/edits',
                                        {'model': MODEL, 'prompt': item['prompt'], 'size': args.size},
                                        [('image', base_img)])
            else:
                result = post_json('/images/generations',
                                   {'model': MODEL, 'prompt': item['prompt'],
                                    'size': args.size, 'n': 1})
            size = save_result(result, dest)
            log[rel] = {'status': 'done', 'mode': item['mode'], 'size': size,
                        'seconds': round(time.time() - started, 1), 'prompt': item['prompt']}
            print(f'DONE {rel} ({size/1e6:.1f}MB, {log[rel]["seconds"]}s)', flush=True)
        except Exception as ex:
            log[rel] = {'status': 'error', 'error': str(ex)[:2000]}
            print(f'ERROR {rel}: {ex}', flush=True)
        with open(LOG, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    print('ALL FINISHED', flush=True)


if __name__ == '__main__':
    main()
