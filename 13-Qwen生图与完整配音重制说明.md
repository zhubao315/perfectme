# 《满分的我》重制（v3）：Qwen-Image 生图 + H3 视频 + 完整配音

> 更新 2026-11-27 ｜ 成片 `07-成片/满分的我-动画版-H3-加长版.mp4`
> 前两版见 `11-动画版H3制作说明.md`（2′32″）与 `12-图片与加长版重制说明.md`（4′03″）

## 为什么重做

v2（H3-Image 生图 + 1.6× 视频 + 原配音）存在三个问题：
1. **H3-Image 不支持负面提示词**，虽然把排除项写进正面描述，但复杂镜头仍出现畸形手、屏幕乱码文字、主体错乱。
2. **配音被 `atempo` 压缩**：manifest 中 6 句溢出（最长 V02 9.52s 压进 5.2s 窗口，1.8×），听感急促、句子不完整；且旧 TTS Key（GPUStack）已失效，Qwen3-TTS 实例处于 PENDING 无法重新合成。
3. **视频与配音时长错配**：1.6× 时间轴 ≈243s，但配音只有 152s，后半段靠 BGM 填充。

## v3 方案

| 环节 | 做法 |
|---|---|
| 图片 | **Qwen-Image-2.1**（OpenAI 兼容 API `http://127.0.0.1:18189/v1`，模型 `qwen-image-2.1`，8 步 Turbo，1280×720）。支持 `negative_prompt`，恢复正常风格前缀 + 角色锚定 + 负面词。变体图走 `/images/edits`（字段 `image[]`，**不支持** `negative_prompt`/`size`），以主图为编辑目标保同机位。 |
| 视频 | **MiniMax H3 图生视频**（`comfyui-minimax-h3-video:18201`），以新生成的 Qwen 分镜图为首帧，时间轴 **1.4×**（≈187s，匹配完整配音），帧数 17k+5 网格（124–362）。 |
| 配音 | 复用 26 条已生成的 Qwen3-TTS 配音文件，**每句按自然时长完整播放、不做 atempo 压缩**；后续台词顺延 0.25s 避免重叠；BGM 循环铺满；响度 −16 LUFS。V26 已存在，全部 26 句齐全。 |
| 字幕 | 由 `mix_full_plan.json` 的实际排程生成 ASS（`build/subs_full.ass`），时间点与配音**逐句精确对齐**，关键词暖金渐变。 |

## 关键修复记录

- Qwen `/images/edits` 只接受 `model/prompt/steps/seed/n/image[]`；传 `negative_prompt` 或 `size` 会 400。
- 3 张问题图（S02 点赞特写、S08 完美九宫格、S14 镜面包围）首轮生成出现"整屏重复头像墙/主体错乱"，已用更明确的构图提示词重生成修复。
- 完整配音排程后总长 187.08s，对应视频时间轴缩放 1.4×（而非 v2 的 1.6×）。

## 复现命令

```bash
# 1. Qwen-Image 生成 33 张图
python3 build/h3_image/build_prompts_qwen.py
python3 build/h3_image/generate_images_qwen.py            # 断点续跑；失败项自动记录，可 --force --only 重试

# 2. H3 视频（1.4× 时间轴）
H3_SCALE=1.4 python3 build/h3/01b-build-manifest-long.py
python3 build/h3/02-generate-clips.py \
  --manifest build/h3_manifest_long.json \
  --clips build/h3_clips_qwen --log build/h3_generate_qwen_log.json --prefix qwen_ --force

# 3. 完整配音混音 + 同步字幕
H3_SCALE=1.4 python3 build/mix_dub_full.py
python3 build/make_subs_full.py

# 4. 合成
H3_SCALE=1.4 python3 build/h3/03b-assemble-long.py

# 5. 刷新网站剧照与成片
python3 build/h3_image/update_site_assets.py
```

## 网站

GitHub Pages 从仓库根目录部署：<https://zhubao315.github.io/perfectme/>
