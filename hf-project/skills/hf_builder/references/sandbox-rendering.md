# HF Sandbox Rendering Quirks

Discovered during video-factory pipeline development (2026-06-11). These are issues where the composition HTML is syntactically valid and passes lint, but the rendered video is wrong.

## Background Color Not Rendering

**Symptom**: HTML has `background: #1a1a2e` in CSS but rendered video shows white background.

**Root cause**: The HF sandbox renderer may not apply CSS class-based backgrounds reliably, especially when CSS resets (`* { margin:0; padding:0; box-sizing:border-box }`) are present.

**Fix — triple-layer background**:
1. `<html style="background:#1a1a2e;">` — on the html tag
2. `<body style="margin:0;padding:0;overflow:hidden;background:#1a1a2e;">` — on body
3. `<div class="scene" style="background:#1a1a2e;">` — on the scene div (inline, not just CSS class)

**Also**: Add `min-height:100%` to `.scene` CSS rule to ensure it fills the viewport.

**Avoid**: CSS resets with `* { box-sizing:border-box }` — these can interfere with the composition wrapper's sizing. Use targeted resets on specific elements instead.

## CSS Custom Properties (var())

See main skill pitfalls section. Summary: `var(--xxx)` references render as browser defaults (white) in the sandbox. Replace ALL with hardcoded values before rendering.

Common variable map:
```
--bg-color → #1a1a2e
--primary-color → #00D4FF
--accent-color → #FF6B6B
--text-color → #FFFFFF
--text-secondary → #A0A0B0
--data-color → #4ECDC4
--font-body → 'Inter','Noto Sans SC',sans-serif
--font-data → 'JetBrains Mono',monospace
--md-radius → 12px
--sm-radius → 8px
```

Also handle chain references: `--bg: var(--xxx)` → resolve to the final value.

## Timeline Registration Failures

**Symptom**: HF reports "Sub-composition timelines not registered after 45000ms" for ALL compositions.

**Common causes**:
1. **JavaScript syntax error in ANY composition** — one bad JS file can block the entire page's script execution. Check brace/paren balance in all script blocks.
2. **`querySelectorAll` with nested quotes** — `"[data-composition-id="beat-1"]"` breaks JS parsing. Use single quotes for the JS string.
3. **Truncated HTML** — LLM output cut off by max_tokens leaves unclosed `<script>` blocks. Add truncation detection.

**Debugging**: Extract script content from each composition and check:
```python
import re
scripts = re.findall(r'<script(?!\s+src)[^>]*>(.*?)</script>', html, re.DOTALL)
for s in scripts:
    if s.count('(') != s.count(')'):
        print(f"PARENS MISMATCH: {s.count('(')}/{s.count(')')}")
    if s.count('{') != s.count('}'):
        print(f"BRACES MISMATCH: {s.count('{')}/{s.count('}')}")
```

## LLM-Generated HTML Quality

When using LLMs to generate composition HTML (instead of hand-authoring):

1. **Increase max_tokens** to 8000+ (4000 is too small for rich HTML with CSS+GSAP)
2. **Add retry mechanism** — if HTML < 3000 chars or missing key elements, retry with stronger prompt
3. **Filter non-HTML content** — MIMO and other models may include reasoning text before/after HTML. Extract only the `<!DOCTYPE html>...</html>` block.
4. **Deduplicate `__timelines` registrations** — auto-fix may add duplicates if LLM already included registration
5. **Remove `tl.play()`** — LLMs often add this; HF controls playback
6. **Replace Math.random()** — LLMs use this for "random" effects; replace with `0.5` or deterministic values
