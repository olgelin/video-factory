# Skills 模块文档
> 自动生成于 2026-07-09 06:37

共 27 个 skill。

## asset_manager

**描述**: (无描述)
**代码行数**: 246
**主要函数**: screenshot_url, download_image, prepare_assets, run
**日志标签**: 下载, 截图, 素材
**SKILL.md**: ❌ 缺失

## audio_mixer

**描述**: (无描述)
**代码行数**: 178
**主要函数**: run_ffmpeg, burn_subtitles, run
**SKILL.md**: ✅

## audio_mixer_lyric

**描述**: (无描述)
**代码行数**: 185
**主要函数**: run_ffmpeg, burn_subtitles, run
**SKILL.md**: ❌ 缺失

## bgm_generator

**描述**: (无描述)
**代码行数**: 66
**主要函数**: run
**SKILL.md**: ✅

## color_grader

**描述**: (无描述)
**代码行数**: 214
**主要函数**: run, _select_palette
**SKILL.md**: ✅

## depth_composer

**描述**: (无描述)
**代码行数**: 124
**主要函数**: run
**SKILL.md**: ✅

## design_system

**描述**: 生成视觉设计系统（配色方案、字体、风格方向）。输出 design.md + design_specs.json
**代码行数**: 522
**主要函数**: select_style_for_topic, generate_scene_variants_fallback, generate_scene_variants, generate_design_md, run
**SKILL.md**: ✅

## hf_builder

**描述**: LLM-driven HyperFrames composition generator. Takes storyboard + design.md, generates scene-specific HTML with auto-GSAP animations, renders to MP4.
**代码行数**: 2028
**主要函数**: call_llm, call_llm_for_html, load_design_system, load_design_specs, generate_scene_html_llm, _fill_template, _auto_fix_taste, _scene_signature
**日志标签**: hf_builder
**SKILL.md**: ✅

## layout_composer

**描述**: (无描述)
**代码行数**: 82
**主要函数**: run
**SKILL.md**: ✅

## lyric_scene_designer

**描述**: (无描述)
**代码行数**: 127
**主要函数**: _load_prompt, run
**SKILL.md**: ❌ 缺失

## lyrics_writer

**描述**: (无描述)
**代码行数**: 323
**主要函数**: generate_lyrics, _generate_fallback_lyrics, run
**SKILL.md**: ✅

## motion_director

**描述**: (无描述)
**代码行数**: 137
**主要函数**: run
**SKILL.md**: ✅

## packager

**描述**: (无描述)
**代码行数**: 97
**主要函数**: run
**日志标签**: packager
**SKILL.md**: ❌ 缺失

## quality_checker

**描述**: (无描述)
**代码行数**: 371
**主要函数**: check_video_basics, check_blank_frames, check_audio_levels, check_subtitle_coverage, check_subtitle_timing, _parse_srt_time, run_full_check, run
**SKILL.md**: ❌ 缺失

## quality_gate

**描述**: V6.0 统一质量关卡（合并 quality_scorer + quality_checker）。HTML 评分 → 视频质检
**代码行数**: 263
**主要函数**: _overall_grade, score_html_scenes, _parse_srt_time, check_video, run
**SKILL.md**: ✅

## quality_scorer

**描述**: (无描述)
**代码行数**: 273
**主要函数**: run, _overall_grade, _dimension_averages, _load_llm_review_prompt, _llm_review_html, _extract_json
**日志标签**: LLM审查, quality_scorer
**SKILL.md**: ❌ 缺失

## script_writer

**描述**: (无描述)
**代码行数**: 477
**主要函数**: _load_prompt, preprocess_numbers, preprocess_text, generate_script, _parse_json_response, _convert_scenes_to_sections, run
**SKILL.md**: ✅

## storyboard

**描述**: (无描述)
**代码行数**: 627
**主要函数**: _load_prompt, detect_visual_type, match_timestamps, _load_real_data, generate_storyboard, run
**日志标签**: storyboard
**SKILL.md**: ✅

## storyboard_lyric

**描述**: (无描述)
**代码行数**: 731
**主要函数**: _load_prompt, detect_visual_type, match_timestamps, _load_real_data, generate_storyboard, run
**日志标签**: storyboard, storyboard_lyric
**SKILL.md**: ❌ 缺失

## style_learner

**描述**: (无描述)
**代码行数**: 287
**主要函数**: call_llm, analyze_style, merge_styles, run
**SKILL.md**: ❌ 缺失

## topic_scout

**描述**: (无描述)
**代码行数**: 358
**主要函数**: get_session, fetch_baidu_hot, fetch_toutiao_hot, fetch_bilibili_hot, fetch_douyin_hot, fetch_v2ex_hot, fetch_all_trending, similarity
**日志标签**: 抖音热搜, B站热搜, future, 热点采集, 百度热搜, 今日头条
**SKILL.md**: ✅

## topic_selector

**描述**: (无描述)
**代码行数**: 533
**主要函数**: select_topic, _select_from_topics_list, _select_from_report, _search_real_data, run
**SKILL.md**: ✅

## transcriber

**描述**: (无描述)
**代码行数**: 200
**主要函数**: run, _fallback_from_voice_durations, _generate_srt_from_segments_v2, _format_srt_time
**日志标签**: transcriber
**SKILL.md**: ✅

## video_renderer

**描述**: (无描述)
**代码行数**: 346
**主要函数**: _fix_duplicate_styles, _simplify_composition_gsap, run_hyperframes_render, _render_fallback_frame, _validate_html_structure, run
**SKILL.md**: ✅

## video_upscaler

**描述**: Video2X 高清修复（可选）。1080p → 超分输出
**代码行数**: 100
**主要函数**: _find_video2x, run
**日志标签**: upscaler
**SKILL.md**: ✅

## visual_director

**描述**: V6.0 电影级视觉导演（合并 color_grader + layout_composer + motion_director + depth_composer）
**代码行数**: 246
**主要函数**: _select_palette, run
**SKILL.md**: ✅

## voice_gen

**描述**: (无描述)
**代码行数**: 190
**主要函数**: run, _convert_numbers_in_script
**SKILL.md**: ✅
