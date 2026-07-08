# edu_music Pipeline 硬性约束

> 违反任一条 → 出 bug。每次跑 pipeline 前检查。

## 结构约束

1. **`.scene` div 宽高必须是 1920×1080**
   - 代码层强制修正，不管 LLM 写什么
   - 参考：`bug-patterns/top-left-corner.md`

2. **禁止双层 `<!DOCTYPE html>`**
   - `_strip_outer_html` 在包裹前剥离
   - 参考：`bug-patterns/top-left-corner.md`

3. **所有 `tl.fromTo/gsap.from` 必须挂在 `tl` 上**
   - 不能在 `tl` 外面裸写 `gsap.to()`
   - 否则 HyperFrames 渲染引擎抓不到

## 视觉约束

4. **BGM 段禁止纯大字报**
   - 歌词场景必须有 visual_type（explain_card/quote_hero/compare/flow 等）
   - 至少 4 种类型轮换
   - 参考：`bug-patterns/bgm-lyric-poster.md`

5. **配音段和 BGM 段风格要一致**
   - 不能教学段深色科技风、BGM 段变成暖色抒情风
   - 配色、光晕、波形条等组件复用

6. **`overflow: hidden` 必须存在**
   - scene div 和 body 都要

## 音频约束

7. **BGM 混合用 `volume=if(lt(t,voice_dur),0.25,1)` 表达式**
   - 不用 `atrim`/`adelay` 手动分段
   - 参考：`bug-patterns/bgm-silence.md`

8. **两遍 loudnorm**（配音+BGM 混合后）
   - 目标：-24 LUFS

## 审查约束

9. **LLM 审查采样 5 个场景**（场景 ≤10 时全查）
   - 均匀间隔采样，覆盖首中尾

10. **quality_checker 必须检查**
    - ffprobe 基础（时长/分辨率/音频轨道）
    - 字幕覆盖率 ≥ 80%
    - 帧采样 3 个时间点

## 链路约束

11. **`lyric_scenes.json` 必须在 `storyboard_lyric` 之前生成**
    - 文件不存在时 storyboard_lyric 要报错
    - 不能静默退化到默认模板

12. **critical_checks 必须验证**
    - voice_gen → `step05_voice.wav`
    - hf_builder → `compositions/beat-*.html`
    - audio_mixer → `step11_final.mp4`
