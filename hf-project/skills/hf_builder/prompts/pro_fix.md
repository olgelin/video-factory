修复以下 HTML 的具体问题。只修复列出的问题，不要改动其他正常的部分。

## 🔴 必须修复的问题
{issues_text}
{extra_guidance}
## 🟢 不要动的部分
{good_text}

## 当前 HTML
```html
{html_preview}
```

## 硬性规则
- 只改问题清单上的项，其他保持原样
- data-composition-id="{composition_id}" data-width="{W}" data-height="{H}" 必须保留
- GSAP 结构不要破坏: tl = gsap.timeline({{paused:true}}) + window.__timelines["{composition_id}"] = tl
- 所有样式用内联 style=""，禁止 `<style>` 块、禁止 `<link>`
- 禁止 CSS opacity:0（GSAP 从 opacity:0 入场就够了）
- 如果问题是"截断"，检查并补全被截断的文字
- 如果问题是"背景色"，把背景改成深色蓝紫渐变(#0A0A1A→#1A0A2E)
- 如果问题是"动画不足"，参考上面的动画模板追加新的 tl.from()，不要替换已有的
- 如果问题是"跑题"或"内容不相关"，根据场景主题重写标题和文字内容
- 只输出完整 HTML（`<!DOCTYPE html>` 开头），不要解释