#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 Qwen-Image-2.1（OpenAI 兼容 API，18189）重新生成全部图片。

接口：POST /v1/images/generations  {"model":"qwen-image-2.1","prompt":...,"negative_prompt":...,"size":"1280x720","steps":8,"n":1}
编辑：POST /v1/images/edits（multipart，image[] 1~2 个）
"""
import argparse, base64, json, mimetypes, os, time, urllib.request, uuid

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BUILD = os.path.join(ROOT, 'build', 'h3_image')
PROMPTS = os.path.join(BUILD, 'prompts_qwen.json')
LOG = os.path.join(BUILD, 'generate_qwen_log.json')
ASSETS = os.path.join(ROOT, '04-分镜图')
BACKUP = os.path.join(BUILD, 'qwen_original_backup')
API = os.environ.get('QWEN_IMAGE_API', 'http://127.0.0.1:18189/v1')
MODEL = 'qwen-image-2.1'
SIZE = os.environ.get('QWEN_IMAGE_SIZE', '1280x720')
TIMEOUT = 900
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def post_json(path, payload):
    req = urllib.request.Request(API + path, data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={'Content-Type': 'application/json'})
    with OPENER.open(req, timeout=TIMEOUT) as r:
        return json.load(r)


def post_multipart(path, fields, images):
    boundary = uuid.uuid4().hex
    chunks = []
    for k, v in fields.items():
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for field, filepath in images:
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
        raise RuntimeError('empty: ' + json.dumps(result)[:300])
    item = data[0]
    blob = base64.b64decode(item['b64_json']) if 'b64_json' in item else None
    if not blob and item.get('url'):
        with OPENER.open(item['url'], timeout=120) as r:
            blob = r.read()
    if not blob or not blob.startswith(b'\x89PNG'):
        raise RuntimeError('bad payload: ' + json.dumps(item)[:300])
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'wb') as f:
        f.write(blob)
    return len(blob)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--limit', type=int)
    ap.add_argument('--force', action='store_true')
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
            print('SKIP', rel, flush=True); continue
        backup = os.path.join(BACKUP, rel)
        if os.path.isfile(dest) and not os.path.isfile(backup):
            os.makedirs(os.path.dirname(backup), exist_ok=True)
            with open(dest, 'rb') as s, open(backup, 'wb') as d:
                d.write(s.read())
        started = time.time()
        try:
            if item['mode'] == 'edit':
                base_img = os.path.join(ASSETS, item['base_image'])
                # edits 接口只接受 model/prompt/steps/seed/n/image[]，不支持 negative_prompt/size
                result = post_multipart('/images/edits',
                                        {'model': MODEL, 'prompt': item['prompt'], 'steps': 8},
                                        [('image[]', base_img)])
            else:
                result = post_json('/images/generations',
                                   {'model': MODEL, 'prompt': item['prompt'],
                                    'negative_prompt': item['negative'],
                                    'size': SIZE, 'steps': 8, 'n': 1})
            n = save_result(result, dest)
            log[rel] = {'status': 'done', 'mode': item['mode'], 'size': n,
                        'seconds': round(time.time() - started, 1)}
            print(f'DONE {rel} ({n/1e6:.1f}MB, {log[rel]["seconds"]}s)', flush=True)
        except Exception as ex:
            log[rel] = {'status': 'error', 'error': str(ex)[:1000]}
            print('ERROR', rel, ex, flush=True)
        with open(LOG, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)
    print('ALL FINISHED', flush=True)


if __name__ == '__main__':
    main()
