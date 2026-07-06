"""
composer — Clean HyperFrames composition engine (V13).

Architecture:
  tokens.py      → :root CSS custom properties per scene
  timeline.py    → narration word-level timing from whisperx transcript
  postprocess.py → LLM HTML cleanup + validation (shared by impl.py + build_v13.py)

Usage:
  import composer
  composer.build_root_css(scene_id)   → :root CSS
  composer.timeline.init(...)         → load transcript
  composer.timeline.for_scene(id, dur) → caption HTML + GSAP
  composer.postprocess.clean(...)      → auto-fix LLM output
  composer.postprocess.validate(...)   → check rendering requirements
"""
from .tokens import build_root_css, SCENE_ACCENTS
from .timeline import CaptionTimeline, init, for_scene
from .postprocess import clean, validate, extract_body

__all__ = [
    "build_root_css", "SCENE_ACCENTS",
    "CaptionTimeline", "init", "for_scene",
    "clean", "validate", "extract_body",
]
