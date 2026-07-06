"""
CSS Token System — generates :root custom properties from style playbook.
Replaces ALL hardcoded rgba()/hex values with CSS variables.
Inspired by OpenMontage's hyperframes_style_bridge.py.
"""
from typing import Dict

# ───────────────────────────────────────────
# DEFAULT / FALLBACK TOKENS (dark cyber-tech)
# ───────────────────────────────────────────
DEFAULT_TOKENS = {
    "--color-bg":          "#0A0A2E",
    "--color-bg-surface":  "#0F1035",
    "--color-bg-elevated": "#141545",
    "--color-fg":          "#E8ECFF",
    "--color-fg-dim":      "#8890B8",
    "--color-fg-muted":    "#6B7DB3",
    "--color-accent":      "#C519FF",
    "--color-accent-glow": "#E080FF",
    "--color-accent-dim":  "rgba(197,25,255,0.35)",
    "--color-danger":      "#FF3344",
    "--color-danger-glow": "#FF6677",
    "--color-danger-dim":  "rgba(255,51,68,0.35)",
    "--color-positive":    "#00FF88",
    "--color-positive-glow":"#80FFBB",
    "--color-positive-dim":"rgba(0,255,136,0.35)",
    "--color-warn":        "#FFB347",
    "--color-warn-glow":   "#FFCC80",
    "--color-warn-dim":    "rgba(255,179,71,0.35)",
    "--color-info":        "#00CCFF",
    "--color-info-glow":   "#80EEFF",
    "--color-info-dim":    "rgba(0,204,255,0.35)",
    "--color-alpha":       "#FF6633",
    "--color-alpha-glow":  "#FF9966",
    "--color-alpha-dim":   "rgba(255,102,51,0.35)",
    "--color-steel":       "#8899AA",
    "--color-steel-glow":  "#AABBCC",
    "--color-steel-dim":   "rgba(136,153,170,0.35)",
    "--font-heading":      "Inter, 'Noto Sans SC', sans-serif",
    "--font-body":         "Inter, 'Noto Sans SC', sans-serif",
    "--font-mono":         "'Space Mono', 'JetBrains Mono', monospace",
    "--ease-entrance":     "cubic-bezier(0.33,1,0.68,1)",
    "--ease-exit":         "cubic-bezier(0.32,0,0.67,0)",
    "--ease-standard":     "cubic-bezier(0.65,0,0.35,1)",
    "--ease-bounce":       "cubic-bezier(0.34,1.56,0.64,1)",
    "--duration-fast":     "0.3s",
    "--duration-normal":   "0.6s",
    "--duration-slow":     "1.0s",
    "--radius-sm":         "8px",
    "--radius-md":         "14px",
    "--radius-lg":         "20px",
    "--radius-round":      "50%",
    "--shadow-card":       "0 4px 24px rgba(0,0,0,0.5)",
    "--shadow-glow":       "0 0 40px",
}

# Per-scene accent overrides (scene_id → token overrides)
SCENE_ACCENTS: Dict[int, Dict[str, str]] = {
    1: {"--color-accent": "#C519FF", "--color-accent-glow": "#E080FF",
        "--color-accent-dim": "rgba(197,25,255,0.35)"},
    2: {"--color-accent": "#FF3355", "--color-accent-glow": "#FF6680",
        "--color-accent-dim": "rgba(255,51,85,0.35)"},
    3: {"--color-accent": "#00CCFF", "--color-accent-glow": "#80EEFF",
        "--color-accent-dim": "rgba(0,204,255,0.35)"},
    4: {"--color-accent": "#FF6633", "--color-accent-glow": "#FF9966",
        "--color-accent-dim": "rgba(255,102,51,0.35)"},
    5: {"--color-accent": "#00FF88", "--color-accent-glow": "#80FFBB",
        "--color-accent-dim": "rgba(0,255,136,0.35)"},
    6: {"--color-accent": "#FF3344", "--color-accent-glow": "#FF6677",
        "--color-accent-dim": "rgba(255,51,68,0.35)"},
    7: {"--color-accent": "#8899AA", "--color-accent-glow": "#AABBCC",
        "--color-accent-dim": "rgba(136,153,170,0.35)"},
}

def build_root_css(sid: int, palette: dict = None) -> str:
    """Generate :root CSS block with custom properties.

    Priority: palette dict > SCENE_ACCENTS[sid] > DEFAULT_TOKENS
    Returns the CSS content (no <style> wrapper).
    """
    tokens = dict(DEFAULT_TOKENS)
    tokens.update(SCENE_ACCENTS.get(sid, {}))

    if palette:
        mapping = {
            "background": "--color-bg",
            "foreground": "--color-fg",
            "accent": "--color-accent",
            "accent_glow": "--color-accent-glow",
            "primary": "--color-accent",
            "danger": "--color-danger",
            "positive": "--color-positive",
            "bg_surface": "--color-bg-surface",
            "bg_elevated": "--color-bg-elevated",
            "fg_dim": "--color-fg-dim",
            "fg_muted": "--color-fg-muted",
        }
        for pk, token_k in mapping.items():
            if pk in palette:
                tokens[token_k] = palette[pk]

    lines = [":root {"]
    for k, v in sorted(tokens.items()):
        lines.append(f"  {k}: {v};")
    lines.append("}")

    return "\n".join(lines)


def build_global_css(sid: int, palette: dict = None) -> str:
    """Generate the full <style> block for a scene composition."""
    root_css = build_root_css(sid, palette)

    return f"""<style>
{root_css}

/* Global reset */
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1920px;height:1080px;overflow:hidden;background:var(--color-bg);font-family:var(--font-body)}}

/* Atmosphere layers */
.bg-gradient{{position:absolute;inset:0;z-index:1;pointer-events:none;
  background:linear-gradient(135deg,var(--color-accent-dim),var(--color-bg));}}
.bg-grid{{position:absolute;inset:0;z-index:2;pointer-events:none;opacity:0.35;
  background-image:linear-gradient(var(--color-accent-dim)1px,transparent 1px),
    linear-gradient(90deg,var(--color-accent-dim)1px,transparent 1px);
  background-size:60px 60px;}}
.bg-glow{{position:absolute;top:50%;left:50%;z-index:3;pointer-events:none;
  width:1200px;height:1200px;transform:translate(-50%,-50%);border-radius:50%;
  background:radial-gradient(circle,var(--color-accent-dim),transparent 70%);}}
.bg-particles{{position:absolute;inset:0;z-index:4;pointer-events:none;opacity:0.12;
  background-image:radial-gradient(1.5px 1.5px at 12% 22%,var(--color-accent),transparent),
    radial-gradient(1px 1px at 28% 68%,var(--color-accent),transparent),
    radial-gradient(1.5px 1.5px at 43% 15%,var(--color-accent),transparent),
    radial-gradient(1px 1px at 58% 78%,var(--color-accent),transparent),
    radial-gradient(2px 2px at 72% 35%,var(--color-accent),transparent),
    radial-gradient(1px 1px at 88% 55%,var(--color-accent),transparent);}}

/* Foreground overlays */
.fg-vignette{{position:absolute;inset:0;z-index:900;pointer-events:none;
  background:radial-gradient(ellipse at center,transparent 45%,rgba(0,0,0,0.7));}}
.fg-scanlines{{position:absolute;inset:0;z-index:700;pointer-events:none;opacity:0.06;
  background:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.05)2px,rgba(0,0,0,0.05)4px);}}

/* HUD corners */
.hud-corner{{position:absolute;pointer-events:none;z-index:800;width:80px;height:80px;}}
.hud-tl{{top:25px;left:25px;border-top:2px solid var(--color-accent-dim);border-left:2px solid var(--color-accent-dim);}}
.hud-tr{{top:25px;right:25px;border-top:2px solid var(--color-accent-dim);border-right:2px solid var(--color-accent-dim);}}
.hud-bl{{bottom:25px;left:25px;border-bottom:2px solid var(--color-accent-dim);border-left:2px solid var(--color-accent-dim);}}
.hud-br{{bottom:25px;right:25px;border-bottom:2px solid var(--color-accent-dim);border-right:2px solid var(--color-accent-dim);}}

/* Content area */
.content{{position:absolute;inset:60px 80px;z-index:10;display:flex;}}

/* Typography */
.glow-text{{text-shadow:0 0 40px var(--color-accent-dim),0 0 80px rgba(0,0,0,0.5);}}
.accent-line{{height:4px;background:linear-gradient(90deg,transparent,var(--color-accent-dim),transparent);margin:16px 0;}}
.big-number{{font-size:140px;font-weight:900;line-height:1;letter-spacing:-0.03em;}}
.metric-label{{font-family:var(--font-mono);font-size:20px;text-transform:uppercase;letter-spacing:0.1em;color:var(--color-fg-muted);}}

/* Card components — light glass on dark */
.card-glass{{background:linear-gradient(135deg,rgba(255,255,255,0.07)0%,rgba(255,255,255,0.03)100%);
  border:2px solid var(--color-accent-dim);border-left:4px solid var(--color-accent);
  border-radius:var(--radius-md);padding:28px 36px;box-shadow:var(--shadow-card);}}
.card-accent{{background:linear-gradient(135deg,rgba(255,255,255,0.09)0%,rgba(255,255,255,0.04)100%);
  border:2px solid var(--color-accent-dim);border-left:4px solid var(--color-accent);
  border-radius:var(--radius-md);padding:28px 36px;
  box-shadow:0 4px 28px var(--color-accent-dim),var(--shadow-card);}}
.card-metric{{background:linear-gradient(180deg,rgba(255,255,255,0.06)0%,rgba(255,255,255,0.02)100%);
  border:2px solid var(--color-accent-dim);border-top:3px solid var(--color-accent);
  border-radius:var(--radius-sm);padding:24px 40px;text-align:center;min-width:240px;
  box-shadow:0 4px 20px rgba(0,0,0,0.45);}}
.card-alert{{background:linear-gradient(135deg,var(--color-danger-dim)0%,rgba(255,30,30,0.03)100%);
  border:2px solid var(--color-danger);border-left:4px solid var(--color-danger);
  border-radius:var(--radius-sm);padding:22px 32px;width:100%;max-width:1300px;
  box-shadow:0 4px 24px var(--color-danger-dim),var(--shadow-card);}}

/* Narration subtitle bar */
.narration-bar{{position:absolute;bottom:50px;left:120px;right:120px;z-index:500;
  background:rgba(0,0,0,0.75);border-top:2px solid var(--color-accent-dim);
  padding:14px 28px;border-radius:var(--radius-sm) var(--radius-sm) 0 0;}}

/* Layout helpers */
.data-panel{{display:flex;gap:32px;flex-wrap:wrap;justify-content:center;align-items:stretch;}}
.vs-divider{{display:flex;align-items:center;justify-content:center;width:80px;
  font-size:48px;font-weight:900;color:var(--color-accent-dim);}}

/* Performance */
.card-glass,.card-accent,.card-metric,.card-alert,.bg-glow,.bg-grid,.bg-particles{{will-change:opacity,transform;}}
</style>"""
