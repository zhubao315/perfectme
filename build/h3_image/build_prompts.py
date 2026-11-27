#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把旧版逐镜提示词改写成适配 minimax-h3-image 的提示词清单。

规则（h3-image 铁律）：
- 固定 6 步 / CFG=1，无 negative_prompt 字段；要排除的内容写进正面描述。
- 默认且上限 2048×2048，不传 4096 以上；分镜用 2048×1152（16:9，仍在上限内）。
- 变体图（b/c）用 /images/edits，第 1 个 image = 主图，保证同机位同构图。
"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC_DOC = '/oc/mov2/02-提示词/拥抱不完美的自己-逐镜出图提示词.md'
OUT = os.path.join(ROOT, 'build', 'h3_image', 'prompts.json')
ASSETS = os.path.join(ROOT, '04-分镜图')

STYLE = ('轻薄半赛璐淡彩动漫风格：弱化黑色轮廓线，改用深蓝灰与暖褐彩色线稿，'
         '赛璐平涂阴影叠加极淡水彩晕染与纸张颗粒纹理，柔和漫射空气光，'
         '朦胧体积光不做强光束，阴影内带微弱环境色晕染，无厚涂笔触，'
         '手绘水彩绘本质感，色彩克制，情绪靠光比表达。16:9 横向构图。')
CLEAN = ('画面干净清晰，构图完整，人物五官自然端正、手指结构正常且每只手只有五根手指、'
         '肢体数量正确，高清细腻。画面中完全没有任何可辨认的文字、汉字、字母、数字、水印、'
         '署名、品牌标识、真实学校标识、APP界面文字或知名IP角色；没有血腥、恐怖或成人内容，'
         '没有噪点、没有过饱和、没有粗糙黑线、没有厚涂油画笔触。')

# 变体图 -> 主图（用 edits 保持同机位同构图）
VARIANTS = {
    '镜头/S03b-洗手间-更消沉.png': ('镜头/S03-洗手间林一.png', '保持相同机位、构图、景别、服装和光照，仅让林一姿态更消沉：肩背明显下沉、头更低、目光下垂、手机几乎垂下，更无力的坐姿。'),
    '镜头/S06b-假笑.png': ('镜头/S06-练习笑容.png', '保持相同机位、构图、景别、服装和光照，仅把表情改为生硬的假笑：嘴角勉强上扬但眼神空洞、不自然。'),
    '镜头/S10b-抬头看虚影.png': ('镜头/S10-虚拟自我登场.png', '保持相同机位、构图、景别、服装和光照，仅让林一抬头看向青蓝色虚拟自我一林，眼神从平静转为意外。'),
    '镜头/S15b-更痛苦.png': ('镜头/S15-捂耳朵.png', '保持相同机位、构图、景别、服装和光照，仅让情绪更痛苦：双手更用力捂耳、眉头更紧、头更低、身体更内缩。'),
    '镜头/S22b-释然微笑.png': ('镜头/S22-暖色光点.png', '保持相同机位、构图、景别、服装和光照，仅让林一露出释然、放松的浅笑，眼神柔和。'),
    '镜头/S26b-伸手动作.png': ('镜头/S26-陈晓伸手.png', '保持相同机位、构图、景别、服装和光照，仅让陈晓伸手的动作更明确：手臂向前伸出、手掌张开、身体微微前倾。'),
    '镜头/S27b-笑更盛.png': ('镜头/S27-真实的笑.png', '保持相同机位、构图、景别、服装和光照，仅让林一的笑容更灿烂自然：眼睛弯起、露出牙齿、身体放松。'),
    '镜头/S31b-放下手机.png': ('镜头/S31-放下手机.png', '保持相同机位、构图、景别、服装和光照，仅让放下手机的动作更明确：手机屏幕朝下放在桌面、手指离开手机、视线转向窗外。'),
}

# 两张角色图在旧详细提示词文档中没有条目，补写优化提示词
CHARACTER = {
    '角色/林一-主形象.png': (
        '主角人像设定图：15岁中国男高中生林一，身高172cm偏瘦，黑色短碎发、发梢略乱，'
        '圆润杏眼、眼下有淡淡青黑，左耳无饰品；身穿深蓝色水手领校服（白色三条领圈、'
        '左胸校徽为空白凹槽）、白色内衬、藏青长裤。他独自坐在狭小洗手间隔间的马桶上，'
        '低头看银色边框手机，屏幕冷光照亮脸庞，屏幕里是一张阳光自拍，与本人疲惫眼神形成反差。'
        '单人居中构图，肩部以上与半身兼顾，背景虚化。'),
    '角色/三人设定表.png': (
        '原创角色三人并排设定图，白色干净背景，人物比例一致、全身立姿：'
        '左侧林一（现实自我）15岁男高中生，黑色短碎发，深蓝水手领校服，左胸校徽为空白凹槽，'
        '眼神疲惫但勉强微笑；中间一林（理想自我）与林一同脸同身高，头发一丝不乱、皮肤通透、'
        '眼中有高光，同款校服笔挺崭新、纽扣反光，全身带青蓝色柔光描边、双脚离地不投影，'
        '左胸校徽是一枚发光的满环，标准微笑直视镜头；右侧陈晓（朋友）15岁女高中生，'
        '齐肩黑发扎低马尾、脸型偏圆、眉毛浓，同款校服袖子挽到小臂，橙色发圈，运动鞋，'
        '表情平静温和。三人之间留出均匀间距，无标注文字。'),
}


def extract_old():
    txt = open(SRC_DOC, encoding='utf-8').read()
    out = {}
    for m in re.finditer(r'^### `([^`]+)`[^\n]*\n```\n(.*?)\n```', txt, re.M | re.S):
        out[m.group(1)] = m.group(2).strip()
    return out


ANCHORS = {
    '[林一]': ('角色林一：15岁中国男高中生，172cm偏瘦，黑色短碎发、发梢略乱，圆润杏眼、'
             '眼下有淡淡青黑，穿深蓝色水手领校服（白色三条领圈、左胸校徽为空白凹槽）、'
             '白色内衬、藏青长裤，银色边框手机。'),
    '[一林]': ('角色一林（虚拟自我）：与林一同脸同身高，头发一丝不乱、皮肤通透、眼中有高光，'
             '同款校服笔挺崭新、纽扣反光，全身带青蓝色柔光描边，左胸校徽是一枚发光的满环，'
             '标准微笑、目光直视镜头。'),
    '[陈晓]': ('角色陈晓：15岁中国女高中生，160cm，齐肩黑发扎低马尾、脸型偏圆、眉毛浓，'
             '笑起来有浅卧蚕，同款水手领校服、袖子挽到小臂，橙色发圈，运动鞋，表情平静。'),
}


def optimize(base, is_variant=False):
    # 去掉旧文档里残留的“无文字/16:9”等片段，统一由 STYLE + CLEAN 覆盖
    base = re.sub(r'(无文字，?|无水印，?|无品牌logo，?|16:9，?|无真实APP.*?，?)+', '', base)
    base = base.replace('[风格前缀]', '')
    for token, desc in ANCHORS.items():
        base = base.replace(token, desc)
    base = re.sub(r'\s+', ' ', base).strip(' ，。')
    parts = [STYLE, base + '。', CLEAN]
    if is_variant:
        parts.insert(1, '这是一张角色表情/动作变体图，必须与主图保持同机位同构图。')
    return ' '.join(parts)


# 针对 H3-Image 实测问题的定向改写（避免复杂手部/多余人物/屏幕文字）
OVERRIDES = {
    '镜头/S02-点赞特写.png': (
        '手机屏幕极端特写构图：整个画面几乎被一部银色边框手机占满，屏幕上是整齐排列的'
        '九宫格动态照片，每张照片上只有一个红色爱心图形，没有任何可辨认文字。'
        '画面前景只有两根自然的手指（拇指）轻触屏幕边缘，手指结构正常，'
        '不出现人物脸部、身体或其他多余手指。背景是虚化的灰蓝色瓷砖墙，屏幕冷光反射，'
        '紧张压抑的氛围。'),
    '镜头/S08-完美九宫格.png': (
        '手机屏幕特写构图：画面中只有一部手机被一只手自然握持，屏幕上是九张排列整齐的'
        '自拍照片，每张照片只有人像和红色爱心图形，没有任何可辨认文字。'
        '手指结构正常、只有五根手指，不出现多余手指。背景虚化的教室，屏幕冷光，'
        '不出现人物脸部大特写。'),
    '镜头/S27-真实的笑.png': (
        '傍晚教室里的近景：15岁中国男高中生林一（黑色短碎发、深蓝色水手领校服、'
        '左胸校徽为空白凹槽）露出真实自然放松的笑容，没有拿手机，也没有看镜头。'
        '背景是傍晚教室，窗外暖橙色夕阳洒入，虚化的木质课桌与窗户清晰可辨。'
        '温暖的逆光勾勒轮廓，神情真诚释然，上方留出柔和明亮的空间。'),
}


def main():
    old = extract_old()
    files = []
    for root, _, fs in os.walk(ASSETS):
        for f in fs:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                files.append(os.path.relpath(os.path.join(root, f), ASSETS))
    files.sort()
    items = []
    for rel in files:
        if rel in VARIANTS:
            main_rel, change = VARIANTS[rel]
            items.append(dict(path=rel, mode='edit', base_image=main_rel,
                              prompt=optimize(change, True),
                              ref_prompt=old.get(main_rel, '')))
        elif rel in CHARACTER:
            items.append(dict(path=rel, mode='generate', prompt=optimize(CHARACTER[rel])))
        elif rel in OVERRIDES:
            items.append(dict(path=rel, mode='generate', prompt=optimize(OVERRIDES[rel])))
        elif rel in old:
            items.append(dict(path=rel, mode='generate', prompt=optimize(old[rel])))
        else:
            raise RuntimeError(f'no prompt for {rel}')
    json.dump(items, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    print(f'wrote {OUT}: {len(items)} prompts '
          f'(generate={sum(i["mode"]=="generate" for i in items)}, '
          f'edit={sum(i["mode"]=="edit" for i in items)})')


if __name__ == '__main__':
    main()
