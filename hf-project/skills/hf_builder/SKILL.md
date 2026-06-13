---
name: hf_builder
description: "LLM-driven HyperFrames composition generator. Takes storyboard + design.md, generates scene-specific HTML with auto-GSAP animations, renders to MP4."
tags: [video, hyperframes, rendering, composition]
---

# HF Builder Skill

## What it does
Takes storyboard.json (from storyboard skill) and generates HyperFrames HTML compositions using LLM, then renders to MP4.

## Architecture
```
storyboard.json → LLM generates scene HTML → auto-GSAP animations → HF CLI → MP4
```

Each scene gets:
- Background layer (glow orbs, grain, vignette)
- Decoration layer (ghost text, light flow, corner brackets)
- Content layer (LLM-generated based on storyboard's concept/depth_layers/narration)
- Auto-generated GSAP entrance animations

## Input (context)
- `storyboard_path` — path to storyboard.json (default: output/storyboard.json)
- `project_root` — project root directory
- `topic` — topic string

## Output (context)
- `rendered_video` — path to rendered MP4
- `hf_html` — path to index.html

## Key Design Decisions

1. **LLM generates HTML only, NOT GSAP** — LLM-generated GSAP code has variable name errors and undefined references. Auto-GSAP based on class names is more reliable.

2. **`<!DOCTYPE html>` format** — Compositions use full HTML documents, NOT `<template>` tags. This matches the working HyperFrames pipeline format.

3. **Sequential playback, same track** — All scenes on `data-track-index="0"` with cumulative `data-start` times. Different tracks with `data-start="0"` causes white screens.

4. **Animation class names** — LLM must use specific class names (title, subtitle, card, badge, etc.) that the auto-GSAP system recognizes.

## LLM Prompt Strategy
- Pass storyboard's concept (visual direction) + narration (content data) separately
- Concept tells LLM HOW to visualize, narration tells it WHAT to display
- Example: concept says "dashboard" → use dashboard layout; narration says "300万热度" → show 300万

## Pitfalls
1. **Don't let LLM write GSAP** — produces `to.from()` instead of `tl.from()`, references undefined variables
2. **Don't use `<template>` tags** — causes white screens in HyperFrames renderer
3. **Don't put scenes on different tracks** — causes white screens, only first scene visible
4. **Don't use `data-start="0"` for all scenes** — they must be sequential (0, 11.1, 19.2, ...)
5. **Remove `<script>` tags from LLM HTML** — they conflict with the outer template's script
