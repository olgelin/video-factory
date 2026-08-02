# LLM Prompt Design for Beautiful Three.js Abstract Scenes

> Research compiled 2026-07-30 for the video-factory pipeline.
> Core question: *How do we describe a visual aesthetic that the LLM can translate into Three.js code — without giving it code to copy?*

---

## Executive Summary

**The Problem:** The current approach gives LLMs code skeletons (`TorusKnotGeometry`, `MeshStandardMaterial`, hardcoded hex colors). LLMs copy-paste the skeleton without understanding aesthetic intent. Results are mediocre.

**The Key Insight:** Image-generation models (Midjourney, DALL-E) prove that **aesthetic language descriptions produce beautiful visuals**. The same approach works for Three.js scenes — if we teach the LLM to *think like a cinematographer/Director of Photography* rather than a code-copying script.

**Recommended Strategy:** Shift from imperative code instructions to **declarative visual language**. Describe the scene as a cinematographer would: mood, composition, lighting quality, color palette, material feel, camera movement, depth, atmosphere. Let the LLM translate that into Three.js API calls using its own knowledge.

---

## 1. The Current Approach vs. What's Needed

### Current (Template-Driven → Amateur Results)

```
❌ "Use TorusKnotGeometry with MeshStandardMaterial, color #6C8CFF"
❌ "Add a light-scan div with a linear gradient"
❌ "Use the following CSS skeleton: ..."
```

Problems:
- LLM treats output as a fill-in-the-blanks exercise
- No understanding of *why* those choices create beauty
- Every scene looks the same (same geometry, same colors)
- The LLM's vast knowledge of Three.js goes unused

### Proposed (Visual Language → Cinematic Results)

```
✅ "A luminous torus knot floating in deep space, brushed aluminum material catching
    rim light from behind, volumetric dust particles drifting in god rays,
    camera slowly orbiting, deep navy to midnight gradient background"
```

Why this works:
- LLMs are trained on vast amounts of visual descriptions (film reviews, art criticism, image captions)
- They already know Three.js APIs — they just need the *intent* to drive API choice
- Aesthetic language is higher-bandwidth: "volumetric god rays" conveys more than 10 lines of code spec

---

## 2. Dimensions of Visual Description (The Aesthetic Vocabulary)

Based on Midjourney prompt engineering research and cinematography principles, here are the dimensions an LLM prompt should cover for Three.js scenes:

### 2.1 Lighting Quality (Most Important for "Cinematic" Look)

| Descriptor | Three.js Translation |
|---|---|
| **Volumetric lighting / god rays** | SpotLight + fog + custom shader rays |
| **Rim lighting / backlight** | DirectionalLight behind subject, high intensity |
| **Cinematic lighting** | Three-point light setup (key, fill, rim) |
| **Rembrandt lighting** | Key light at 45°, strong chiaroscuro |
| **Soft diffused lighting** | AmbientLight high + HemisphereLight |
| **Neon glow** | PointLight with bloom post-processing |
| **Moody / low-key** | Single light source, deep shadows |
| **Ethereal glow** | High ambient + emissive materials |
| **Golden hour** | Warm directional + long shadows |
| **Crepuscular rays** | SpotLight through volumetric fog |

**Midjourney keywords proven to produce beautiful lighting:** `Cinematic Lighting`, `Volumetric`, `Rim Lights`, `Ethereal Lighting`, `Moody Lighting`, `Epic Light`, `Rembrandt Lighting`, `Soft Lighting`, `Accent Lighting`, `Contre-Jour`, `Low-Key Lighting`, `Backlight`.

### 2.2 Material Feel

| Descriptor | Three.js Translation |
|---|---|
| **Brushed metal / matte** | MeshStandardMaterial, roughness 0.6-0.8, metalness 0.8-1.0 |
| **Polished chrome / mirror** | MeshStandardMaterial, roughness 0.0-0.15, metalness 1.0 |
| **Glossy plastic** | MeshStandardMaterial, roughness 0.2-0.4, metalness 0.0 |
| **Glass / crystal / refractive** | MeshPhysicalMaterial, transmission 0.9+, roughness 0.0 |
| **Velvet / soft matte** | MeshStandardMaterial, roughness 0.9+ |
| **Iridescent / oil slick** | Custom shader or MeshPhysicalMaterial with thinFilm |
| **Emissive / self-illuminating** | MeshStandardMaterial with emissive > 0 |
| **Wireframe / holographic** | MeshBasicMaterial wireframe + glow |
| **Liquid metal / mercury** | MeshStandardMaterial, roughness 0.1, metalness 1.0, envMap |
| **Carbon fiber / textured** | MeshStandardMaterial with normalMap + roughnessMap |

**Midjourney material keywords:** `Chrome`, `Glass`, `Crystal`, `Gold`, `Silver`, `Bronze`, `Neon`, `Holographic`, `Iridescent`, `Carbon Fiber`, `Liquid Metal`, `Mirror Finish`, `Frosted Glass`, `Anodized`, `Brushed`.

### 2.3 Composition & Camera

| Descriptor | Three.js Translation |
|---|---|
| **Hero shot / low angle** | Camera at y < subject, looking up |
| **Bird's eye / top-down** | Camera high above, looking down |
| **Dutch angle / tilted** | Camera roll rotation for unease |
| **Shallow depth of field** | BokehPass2 post-processing |
| **Wide angle / immersive** | FOV 80-100, camera close to subject |
| **Telephoto / flat** | FOV 20-40, camera far from subject |
| **Tracking / dolly shot** | Smooth camera position animation |
| **Orbital / circular** | Camera orbits subject with lookAt |
| **Push-in / zoom** | Camera z-translation toward subject |
| **Rule of thirds** | Subject offset to 1/3 intersections |

### 2.4 Color Palette (Mood & Atmosphere)

| Palette Name | Use Case | Hex Reference |
|---|---|---|
| **Cyberpunk / Synthwave** | Tech, energy, retro-future | #FF007F, #00D4FF, #7000FF on dark |
| **Deep Ocean / Abyss** | Mystery, depth, calm | #0A1128, #1B2A4A, #2D5F8A |
| **Golden Hour / Warm** | Hope, warmth, nostalgia | #FF6B35, #FFB347, #1A0F2E |
| **Neon Noir** | Gritty, urban, contrast | #FF2A6D, #05D9E8, #01012B |
| **Monochrome + Accent** | Elegant, focused | #FFFFFF, #888888, #222222 + one vivid |
| **Pastel Dream** | Soft, ethereal, calm | #FFE5EC, #E0C3FC, #B8D4E3 |
| **Molten / Volcanic** | Power, destruction, heat | #FF4500, #FFD700, #1A0000 |
| **Arctic / Cryo** | Cold, sterile, future | #E0F0FF, #A0D0FF, #4080C0 |
| **Emerald / Botanical** | Nature, growth, organic | #004D40, #2ECC71, #A8E6CF |

### 2.5 Atmosphere & Environment

| Descriptor | Three.js Translation |
|---|---|
| **Fog / mist / haze** | scene.fog = new THREE.FogExp2(color, density) |
| **Dust motes / particles** | BufferGeometry Points with slow animation |
| **God rays / crepuscular** | Volumetric light shafts |
| **Smoke / volumetric** | Semi-transparent animated planes |
| **Stars / space** | Starfield particle system |
| **Underwater caustics** | Light pattern projection on surfaces |
| **Heat haze / shimmer** | Post-processing distortion |
| **Rain / precipitation** | Falling particle system |
| **Aurora / northern lights** | Animated gradient planes with blending |

### 2.6 Motion & Animation Quality

| Descriptor | Implementation |
|---|---|
| **Slow, drifting, weightless** | Very slow rotations (0.1-0.3 rad/s), floating y oscillation |
| **Sharp, precise, mechanical** | Discrete step animations, no easing |
| **Organic, fluid, breathing** | Sine-based scale oscillation, perlin noise motion |
| **Explosive, impactful** | Fast scale-up + overshoot + settle |
| **Hypnotic, meditative** | Constant slow rotation, repeating patterns |
| **Cinematic slow-motion** | Time scale < 1.0, smooth interpolation |
| **Staggered / sequential** | Elements animate in sequence with delay |
| **Elastic / bouncy** | Elastic easing on entrances |

### 2.7 Post-Processing (The "Cinematic" Secret Sauce)

| Effect | Purpose |
|---|---|
| **Bloom (UnrealBloomPass)** | Makes bright areas glow — essential for neon/emissive |
| **Vignette** | Darkens edges, focuses attention |
| **Film grain / noise** | Adds texture, removes "too clean CG" look |
| **Chromatic aberration** | Slight RGB split at edges — cinematic lens feel |
| **Color grading (LUT)** | Shifts entire color palette for mood |
| **Depth of field (BokehPass)** | Blurs background, cinematic focus |
| **Ambient occlusion (SAOPass)** | Contact shadows, depth, realism |
| **Tone mapping (ACESFilmic)** | Film-like highlight rolloff |

**Key finding:** Nearly all "cinematic" Three.js repos on GitHub use shader-based post-processing. The difference between amateur and professional is almost entirely post-processing.

---

## 3. Midjourney Prompt Structure → Three.js Prompt Structure

### How Midjourney Structures Prompts (Proven Aesthetic Formula)

```
[Subject/Scene] + [Style/Medium] + [Lighting] + [Color Palette] + [Composition] + [Atmosphere/Mood] + [Quality Modifiers]
```

Example: `"abstract geometric torus floating in void, brushed gold material, volumetric rim lighting, deep navy and amber palette, hero low-angle shot, ethereal fog atmosphere, cinematic, 8K, photorealistic render"`

### Translating to Three.js Scene Prompts

The same formula works for Three.js prompts:

```
[Geometry/Subject] + [Material Feel] + [Lighting Setup] + [Color Palette] + [Camera & Composition] + [Atmosphere] + [Motion Quality] + [Post-Processing]
```

Example prompt for an LLM:
```
"Create a Three.js abstract scene:
- A complex interlocking geometric form (like three nested torus knots at different scales)
- Materials: brushed dark metal (high roughness, slight anisotropy), with internal surfaces glowing warm amber
- Lighting: a single strong rim light from behind-right creates dramatic silhouettes, subtle fill from ambient
- Palette: deep indigo background (#0A0E27), warm amber (#FFB347) glow from within, cool rim (#6CB4FF)
- Camera: slowly orbiting at eye level, slight upward angle (hero shot)
- Atmosphere: sparse dust particles floating in slight blue fog
- Motion: geometries rotate very slowly on different axes, creating a sense of mechanical precision
- Post-processing: subtle bloom on the emissive surfaces, vignette, ACES tone mapping
- Mood: contemplative, powerful, futuristic"
```

---

## 4. What Makes Three.js Scenes Look Amateur vs. Cinematic

### Amateur Tells (from analysis of GitHub repos and common patterns)

| Problem | Why It Happens | Fix |
|---|---|---|
| **Flat lighting** | Only AmbientLight, no directional/shadows | Three-point lighting setup |
| **Pure black background** | No atmosphere, no fog, no gradient | Add fog, gradient background, particles |
| **Default materials** | MeshBasicMaterial, solid colors | MeshStandardMaterial/PhysicalMaterial with roughness/metalness |
| **No post-processing** | Raw WebGL render | UnrealBloomPass, vignette, tone mapping |
| **Static camera** | Fixed perspective | Orbit, dolly, subtle idle sway |
| **Too-perfect geometry** | Default segments, no variation | Bevels, wireframe overlay, slight random displacement |
| **Color vomit** | Too many saturated colors | Limited palette (3-5 colors max) |
| **No depth cues** | Everything in focus | Fog, DoF, atmospheric perspective |
| **Jarring animations** | Linear easing, too fast | EaseInOutCubic, slow movements |
| **Empty scene** | One object, no context | Particles, grid floor, ambient elements |

### Cinematic Tells (from top Three.js showcase projects)

| Quality | Implementation |
|---|---|
| **Atmospheric depth** | Exponential fog, color-matched to palette |
| **Material richness** | PBR materials with roughness/metalness variation |
| **Light intentionality** | Clear key light direction, motivated fill |
| **Glow/bloom** | UnrealBloomPass on emissive surfaces |
| **Smooth motion** | GSAP with custom easing, or slow continuous rotation |
| **Compositional strength** | Subject placement follows rule of thirds |
| **Color harmony** | Analogous or complementary limited palettes |
| **Particle atmosphere** | Floating particles add scale and depth |
| **Lens simulation** | Chromatic aberration, vignette, slight barrel distortion |

---

## 5. Existing Work: LLM + Three.js/Creative Coding

### Directly Relevant Projects

| Project | Stars | Description |
|---|---|---|
| **[KyaniteLabs/liminal](https://github.com/KyaniteLabs/liminal)** (aka Sinter) | 3★ | AI creative coding studio — generates p5.js, GLSL, and **Three.js** from natural language. Uses an LLM backend. The key pattern: sends prompt → LLM generates creative code → renders in browser. |
| **[ninjarz/brick-flow-agent](https://github.com/ninjarz/brick-flow-agent)** | 1★ | Browser-based 3D workspace with React, Three.js, LDraw parts, and **optional LLM generation**. |
| **[XGRIDS-3D/Interactive-3D-Scene-Creation-via-LLM](https://github.com/XGRIDS-3D/Interactive-3D-Scene-Creation-via-LLM-Driven-Procedural-Generation)** | 10★ | LLM-driven 3D scene creation via procedural generation (Unreal Engine, but the multi-agent approach is relevant). |

### Adjacent / Pattern Reference

| Project | Stars | Relevance |
|---|---|---|
| **[willwulfken/MidJourney-Styles-and-Keywords-Reference](https://github.com/willwulfken/MidJourney-Styles-and-Keywords-Reference)** | Major | Massive reference of aesthetic keywords organized by: Themes, Design Styles, Artists, Materials, Lighting, Colors, etc. Directly usable as an aesthetic vocabulary bank for scene prompts. |

### Cinematic Three.js Reference Projects (for quality benchmarks)

Notable cinematic Three.js projects on GitHub (all use post-processing + shaders):
- **Gargantua Blackhole**: Raymarched accretion disk, shader post-processing
- **Christmas Scene**: Expressive shaders, comic-inspired, bold lighting, minimal composition
- **Project Universe**: Cinematic 3D space journey with R3F + GSAP
- **Cinematic Ocean**: Advanced Water + Sky shaders, scroll-driven camera

**Pattern**: All "cinematic" Three.js projects use:
1. Custom GLSL shaders
2. Post-processing (bloom, tone mapping, DoF)
3. PBR materials (MeshStandardMaterial/PhysicalMaterial)
4. Atmospheric elements (fog, particles)
5. Intentional camera work

---

## 6. Recommended Prompt Design Patterns

### Pattern A: The "Cinematographer's Brief" (Recommended Primary Approach)

Structure the prompt like a Director of Photography's shot brief:

```markdown
You are a Three.js creative coder and cinematographer. Create an abstract 3D scene
based on this visual brief:

SCENE: [what we're looking at]
MOOD: [emotional quality]
LIGHTING: [how light shapes the scene — key/fill/rim directions]
MATERIALS: [how surfaces feel — roughness, metalness, special qualities]
COLOR PALETTE: [3-5 specific colors with roles]
CAMERA: [position, movement, lens feel]
ATMOSPHERE: [fog, particles, environmental elements]
MOTION: [how things move, pacing, rhythm]
POST-PROCESSING: [bloom, vignette, color grade, etc.]

Translate this into Three.js code using MeshStandardMaterial, proper lighting
(not just AmbientLight), and post-processing. Use your knowledge of what makes
3D scenes look professional.
```

### Pattern B: The "Reference Image" Technique

Describe the scene as if describing a reference photo:

```markdown
Imagine a photograph: [geometric form] shot with a [lens type] lens at [aperture].
The [material type] surface catches [lighting description]. In the background,
[atmosphere elements]. The color grade is [film stock / LUT reference].

Create this scene in Three.js.
```

### Pattern C: "Aesthetic Constraint Sandwich"

Layer constraints from abstract to concrete:

1. **Top layer (mood/feeling):** "Ethereal, futuristic, meditative"
2. **Middle layer (visual qualities):** "Soft volumetric lighting, brushed metal, deep blue gradients, floating particles"
3. **Bottom layer (technical hints):** "Use MeshStandardMaterial (not Basic), fog, and UnrealBloomPass"

The LLM connects the abstract to the concrete through its own knowledge.

### Pattern D: "What to Avoid" / Negative Prompting

Explicitly list amateur patterns to avoid:

```markdown
AVOID:
- Flat ambient-only lighting
- Pure black (#000000) backgrounds
- MeshBasicMaterial (use MeshStandardMaterial)
- Static cameras
- Single objects in empty space
- Default segment counts (use at least 64 segments for curves)
- Linear animation easing
- No post-processing pipeline
```

---

## 7. Practical Prompt Template for video-factory

Based on all findings, here's a concrete prompt template:

```markdown
## Role
You are a Three.js cinematographer. Your task is to create a single HTML file
containing a beautiful, cinematic abstract 3D scene. Think like a Director of
Photography, not a code-copying script.

## Visual Brief
{Insert scene description using the dimensional vocabulary above}

## Technical Requirements
- Use Three.js from CDN (importmap or script tag)
- Use MeshStandardMaterial or MeshPhysicalMaterial for all geometry
- Include proper lighting: at minimum a key light + fill + rim setup
- Add atmospheric elements: fog, floating particles, or both
- Include post-processing: at minimum UnrealBloomPass + tone mapping
- Camera should have subtle continuous motion
- Animations should use smooth easing (cubic-bezier or GSAP power2.inOut)

## Anti-Patterns to Avoid
- Do NOT use MeshBasicMaterial
- Do NOT use pure black (#000000) as background
- Do NOT create a static scene with no camera movement
- Do NOT use only AmbientLight
- Do NOT create isolated geometry in empty space

## Output Format
A single, complete, self-contained HTML file that opens and renders correctly
in any modern browser. Include all imports via CDN.
```

---

## 8. Key Findings Summary

1. **The vocabulary matters more than the code.** Midjourney's success proves that rich aesthetic language produces beautiful results. The same approach transfers to Three.js.

2. **LLMs already know Three.js.** The problem isn't knowledge — it's that code skeletons suppress the LLM's ability to make creative choices. Free the LLM from skeletons.

3. **Post-processing is the #1 differentiator.** Nearly all "cinematic" Three.js projects use bloom, tone mapping, and atmosphere effects. Amateur projects skip these entirely.

4. **The Midjourney prompt structure is a proven template.** `[Subject] + [Material] + [Lighting] + [Palette] + [Camera] + [Atmosphere] + [Quality]` — this structure works for 3D scenes too.

5. **Negative prompting is effective.** Explicitly listing what to avoid (MeshBasicMaterial, flat lighting, static camera) prevents common amateur patterns.

6. **KyaniteLabs/liminal (Sinter)** is the most directly relevant existing project — it already does LLM → Three.js/p5.js/GLSL generation, proving the approach works.

7. **The "Cinematographer's Brief" format** — borrowing from film production — is likely the most effective prompt structure because it maps naturally to how LLMs understand visual aesthetics.

---

## 9. Next Steps

1. **Build an aesthetic vocabulary bank** from the Midjourney Styles reference, categorized by: Lighting, Materials, Color Palette, Composition, Atmosphere, Mood, Motion

2. **Create 5-10 "Gold Standard" scene briefs** that produce consistently beautiful results. These become the training examples for the pipeline.

3. **A/B test prompt patterns**: Code skeleton vs. Cinematographer's Brief vs. Reference Image vs. Aesthetic Constraint Sandwich

4. **Build a quality rubric** for evaluating LLM-generated Three.js scenes: lighting quality, material correctness, composition, atmosphere, motion smoothness, post-processing use

5. **Implement a two-pass generation**: Pass 1 = LLM generates scene from visual brief → Pass 2 = separate review LLM checks for amateur patterns (flat lighting, BasicMaterial, static camera, no post-processing) and requests fixes

---

## Sources

- Three.js Official Documentation: Materials, Post-Processing, Lighting
- [willwulfken/MidJourney-Styles-and-Keywords-Reference](https://github.com/willwulfken/MidJourney-Styles-and-Keywords-Reference) — Aesthetic keyword taxonomy
- [KyaniteLabs/liminal](https://github.com/KyaniteLabs/liminal) — LLM-powered creative coding studio (Three.js, p5.js, GLSL)
- [XGRIDS-3D/Interactive-3D-Scene-Creation-via-LLM](https://github.com/XGRIDS-3D/Interactive-3D-Scene-Creation-via-LLM-Driven-Procedural-Generation) — Multi-agent LLM 3D scene creation
- GitHub search: "cinematic three.js" repos — Post-processing and shader patterns
- Current video-factory scene_system.md and SCENE_PROMPT.md — Baseline approach for comparison
