# 双生成函数并存（后处理加错函数，生产完全不生效）

## 症状

LLM 生成的 HTML 在 `</script>` 后漏出裸 Markdown 说明文字（"视觉解析""数据呈现建议"）。连续改了两轮清理逻辑都"没生效"，裸文字反复跑进画面。

## 反推链

1. 看视频 → 画面有裸 Markdown 文字
2. grep beat HTML → `</script>` 后确实有裸文字
3. 为什么清理函数没拦？→ 清理函数 `_clean_bare_text_after_script` 加在了 `generate_scene_html_llm`（旧回退函数）里
4. 为什么生产不生效？→ 实际生产走的是 `_single_llm_generate`（主路径），从不调用旧函数
5. 为什么没被发现？→ 两个函数并存，名字相似，改的时候没确认"这是不是实际生产路径"

## 根因

**双 LLM 生成函数并存**（`_single_llm_generate` 主路径 vs `generate_scene_html_llm` 回退路径），两套后处理逻辑。改一个函数，另一个路径完全不知道。比写错逻辑更隐蔽——不报错，只是"没跑"。

## 修复（2026-09-21）

删掉旧的 `generate_scene_html_llm`（模板+LLM 混合体）+ 它的孤立依赖（`_fill_template`/`_check_diversity`/`_auto_fix_taste`/`TEMPLATES`/`_PER_TYPE_ACCENT`），回退路径单一职责直接 `fallback_scene_html`。净删 357 行死代码。

## 预防

1. 加任何后处理/清理逻辑前，先确认"这个函数是不是实际生产路径"——grep 调用链
2. 删旧代码要彻底：旧函数 + 孤立依赖一起删，不要留新旧并存的隐患
3. 改完 grep 残留引用 + 确认依赖孤立 + import 验证关键函数齐全
