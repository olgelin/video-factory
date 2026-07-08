# BGM 段变成大字报

## 症状

配音结束后的纯 BGM 段（beat-20 ~ beat-31），画面全是"歌词大字居中 + 光晕背景"，没有任何教学型视觉概念（explain_card/compare/quote_hero 等）。

和教学段（beat-1 ~ beat-19）的丰富画面完全不匹配。

## 反推链

1. 人眼看视频 → BGM 段全是歌词大字
2. 检查 beat-20.html → 结构：光晕 + 波形条 + 80px 歌词居中
3. 检查 beat-25/30 → 同样结构，没有 visual_type
4. 找 `lyric_scenes.json` → 文件不存在
5. `lyric_scene_designer` 是生成这个文件的地方 → 没跑或跑了没输出
6. `storyboard_lyric` 读不到 `lyric_scenes.json` → 所有歌词场景退化到默认模板（纯大字报）

## 根因

**`lyric_scene_designer` 的产出文件丢失**，导致下游拿不到视觉概念，全链路退化。

## 修复方向

1. 确保 `lyric_scene_designer` 在 `storyboard_lyric` 之前一定执行
2. 如果 `lyric_scenes.json` 不存在，`storyboard_lyric` 要报错而非静默降级
3. BGM 场景至少应该有 3-4 种视觉类型轮换，不能全是同一种

## 预防

- 关键中间文件（如 `lyric_scenes.json`）设为 `critical_checks`
- 下游 skill 读不到上游产出时 **报错** 而非默默退化
