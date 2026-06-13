# 🎬 Video Factory

15-skill autonomous video production pipeline. From topic research to final MP4 in one command.

## Features

- **Hot topic research** — Multi-platform scraping (Toutiao, Baidu, V2EX, Bilibili)
- **AI script writing** — Xiaomi MiMo LLM, "Ali厂长" tech style
- **Voice cloning** — VoxCPM2 neural TTS
- **BGM generation** — ACE-Step 1.5 music model
- **HyperFrames rendering** — GSAP-powered HTML compositions → MP4
- **Auto transcription** — faster-whisper word-level timestamps
- **Audio mixing** — Voice + BGM + video synthesis

## Quick Start

```bash
# Install
pip install -r requirements.txt
export XIAOMI_API_KEY=your_key

# Run full pipeline
python scripts/orchestrator.py --topic "Your Topic"

# List available skills
python scripts/orchestrator.py --list

# Skip expensive steps (dev mode)
python scripts/orchestrator.py --topic "Test" --skip voice_gen bgm_generator
```

## Architecture

```
topic_scout → topic_selector → script_writer → lyrics_writer
                                                  ↓
              style_learner                     bgm_generator
                  ↓                                ↓
              design_system                   audio_mixer ← voice_gen ← transcriber
                  ↓                               ↓
              storyboard → hf_builder → video_renderer → packager → final.mp4
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `XIAOMI_API_KEY` | ✅ | Xiaomi MiMo API key |
| `DEEPSEEK_API_KEY` | ❌ | DeepSeek fallback |
| `VOXCPM_MODEL` | ❌ | VoxCPM2 model path |
| `ACESTEP_ROOT` | ❌ | ACE-Step package path |

## License

MIT
