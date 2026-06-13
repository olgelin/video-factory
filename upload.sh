#!/bin/bash
KEY=$(grep XIAPING_API_KEY E:/Hermes-Agent/.env | tail -1 | cut -d'=' -f2)
ZIP="E:/Hermes-Agent/workspace/xiaoshan/video-factory/video-factory-v3.0.0.zip"

curl -s -X POST https://xiaping.coze.com/api/skills \
  -H "Authorization: Bearer *** \
  -F "name=video-factory" \
  -F "description=15-skill autonomous video production pipeline with topic research, script generation, voice cloning, BGM composition, HyperFrames HTML rendering, and final MP4 synthesis." \
  -F 'trigger=["video factory","短视频制作","视频生产线"]' \
  -F 'category=["video"]' \
  -F 'tags=["video","pipeline","automation","ai-video"]' \
  -F "version=3.0.0" \
  -F "requires_api_key=true" \
  -F 'pledge={"agreed":true}' \
  -F "file=@${ZIP}"
