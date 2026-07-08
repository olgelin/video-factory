# BGM 单独段静音

## 症状

配音段（0-108s）音视频正常。配音结束后（108-180s）BGM 段画面正常但完全静音。

## 反推链

1. 人耳听 → 后半段没声音
2. ffprobe 验证 → 140s 处 -91dB（完全静音）
3. 检查中间文件 `mixed_audio.wav` → 180s 时长正常，但 150s+ 波形全是零
4. 检查 `audio_mixer_lyric/impl.py` → 使用浮点 `voice_dur=108.6s` 做 `atrim`/`adelay`，浮点精度导致 ffmpeg concat 错位
5. 旧方案用了复杂的 `asplit/concat/atrim/adelay` 滤镜链，任何一环精度出问题就静音

## 根因

**ffmpeg `atrim`/`adelay` 对浮点秒数精度敏感**，改用 `volume` 表达式一行解决。

## 修复（2026-07-09）

将复杂滤镜链替换为：
```
volume=if(lt(t,voice_dur),0.25,1)
```
配音时间段 BGM 音量 25%，配音结束后正常 100%。无需分段、无需 concat。

## 预防

- 凡是 ffmpeg 时间操作，优先用 `if(lt(t,N)...)` 表达式，不用 `atrim`/`adelay` 手动分段
