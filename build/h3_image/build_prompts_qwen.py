#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""为 Qwen-Image-2.1 生成提示词清单：恢复旧文档风格前缀 + 角色锚定 + 负面提示词。

Qwen-Image 支持 negative_prompt（不像 H3-Image 必须把排除项写进正面），
所以这里沿用原项目经过验证的提示词结构，并做轻度优化：
- 展开 [风格前缀] / [林一] / [一林] / [陈晓] 占位符
- 变体图用 /images/edits（Qwen-Image 也支持），保证同机位
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = '/oc/mov2/02-提示词/拥抱不完美的自己-逐镜出图提示词.md'
OUT = os.path.join(ROOT, 'build', 'h3_image', 'prompts_qwen.json')
ASSETS = os.path.join(ROOT, '04-分镜图')

STYLE = ('轻薄半赛璐淡彩动漫风格：弱化黑色轮廓线，改用深蓝灰与暖褐彩色线稿，'
         '赛璐平涂阴影上叠加极淡的水彩晕染与纸张颗粒纹理，柔和漫射空气光，'
         '朦胧体积光不做强光束，阴影内带微弱环境色晕染，无厚涂笔触，'
         '水彩绘本质感，色彩克制，情绪靠光比表达。16:9，无文字，无水印。')
NEG = ('文字, 汉字, 水印, 署名, 真实学校标识, 品牌logo, 真实APP界面文字, '
       '二次元知名IP角色, 崩坏的手, 多指, 六指, 多余肢体, 畸变脸, '
       '血腥, 恐怖, 成人内容, 低清, 噪点, 过饱和, 粗糙黑线, 厚涂, 油画笔触')
ANCHORS = {
    '[林一]': ('林一：15岁中国男高中生，172cm偏瘦，黑色短碎发、发梢略乱，圆润杏眼、'
             '眼下淡淡青黑，深蓝色水手领校服（白色三条领圈、左胸校徽为空白凹槽）、'
             '白色内衬、藏青长裤。'),
    '[一林]': ('一林（虚拟自我）：与林一同脸同身高，头发一丝不乱、皮肤通透、眼中有高光，'
             '同款校服笔挺崭新、纽扣反光，全身带青蓝色柔光描边，左胸校徽为发光的满环。'),
    '[陈晓]': ('陈晓：15岁中国女高中生，160cm，齐肩黑发扎低马尾、脸型偏圆、眉毛浓，'
             '笑起来有浅卧蚕，同款水手领校服、袖子挽到小臂，橙色发圈，运动鞋。'),
}
CHARACTER = {
    '角色/林一-主形象.png': (
        '主角：一名15岁中国男高中生"林一"，身高172cm偏瘦，黑色短碎发、发梢略乱，圆润杏眼、'
        '眼下淡淡青黑，穿深蓝色水手领校服（白色三条领圈、左胸校徽为空白凹槽）、白色内衬。'
        '他独自坐在狭小洗手间隔间的马桶上，低头看手机，屏幕冷光照亮他的脸，'
        '屏幕里是一张阳光灿烂的笑脸自拍，与本人疲惫的眼神形成反差。构图居中，16:9。'),
    '角色/三人设定表.png': (
        '原创角色三视图设定表，白色背景，同一画风：'
        '①林一（现实自我）15岁男高中生，黑色短碎发，深蓝水手领校服，左胸校徽为空白凹槽，'
        '眼神疲惫但勉强微笑；②一林（理想自我）与林一同脸同身高，头发一丝不乱，皮肤通透，'
        '眼中高光，同款校服笔挺反光，全身带青蓝色柔光描边，左胸校徽是发光圆环，'
        '标准微笑直视镜头；③陈晓（朋友）15岁女高中生，齐肩黑发扎低马尾，脸型偏圆，'
        '浓眉，挽起袖子，橙色发圈，运动鞋，表情平静。三人并排，比例一致，16:9。'),
}
VARIANTS = {
    '镜头/S03b-洗手间-更消沉.png': '镜头/S03-洗手间林一.png',
    '镜头/S06b-假笑.png': '镜头/S06-练习笑容.png',
    '镜头/S10b-抬头看虚影.png': '镜头/S10-虚拟自我登场.png',
    '镜头/S15b-更痛苦.png': '镜头/S15-捂耳朵.png',
    '镜头/S22b-释然微笑.png': '镜头/S22-暖色光点.png',
    '镜头/S26b-伸手动作.png': '镜头/S26-陈晓伸手.png',
    '镜头/S27b-笑更盛.png': '镜头/S27-真实的笑.png',
    '镜头/S31b-放下手机.png': '镜头/S31-放下手机.png',
}
OVERRIDES = {
    '镜头/S02-点赞特写.png': (
        '手机屏幕极端特写：双手握着银色边框手机，屏幕上是社交动态的九宫格点赞，'
        '满屏红色爱心，点赞数从98跳到99；冷色环境反射，背景是虚化的洗手间瓷砖；'
        '紧张、空洞、被注视的窒息感。不出现任何真实APP名称、图标或界面文字。'),
    '镜头/S27-真实的笑.png': (
        '傍晚教室里的近景：林一露出真实、自然、放松的笑容——没有拿手机，也没有看镜头；'
        '暖色夕阳从窗户洒入，虚化的木质课桌，真诚、释然。上方留出柔和明亮的空间。'),
}


def extract():
    txt = open(SRC, encoding='utf-8').read()
    return {m.group(1): m.group(2).strip()
            for m in re.finditer(r'^### `([^`]+)`[^\n]*\n```\n(.*?)\n```', txt, re.M | re.S)}


def clean(base):
    base = re.sub(r'\s+', ' ', base).strip(' ，。')
    base = base.replace('[风格前缀]', '')
    for k, v in ANCHORS.items():
        base = base.replace(k, v)
    return STYLE + ' ' + base


def main():
    old = extract()
    files = []
    for root, _, fs in os.walk(ASSETS):
        for f in fs:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                files.append(os.path.relpath(os.path.join(root, f), ASSETS))
    files.sort()
    items = []
    for rel in files:
        if rel in VARIANTS:
            items.append(dict(path=rel, mode='edit', base_image=VARIANTS[rel],
                              prompt=clean('保持原图的机位、构图、景别、服装和光照，仅改变表情或细微动作。' + old.get(rel, '')),
                              negative=NEG))
        elif rel in OVERRIDES:
            items.append(dict(path=rel, mode='generate', prompt=clean(OVERRIDES[rel]), negative=NEG))
        elif rel in CHARACTER:
            items.append(dict(path=rel, mode='generate', prompt=clean(CHARACTER[rel]), negative=NEG))
        elif rel in old:
            items.append(dict(path=rel, mode='generate', prompt=clean(old[rel]), negative=NEG))
        else:
            raise RuntimeError('no prompt: ' + rel)
    json.dump(items, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print('wrote', OUT, len(items))


if __name__ == '__main__':
    main()
