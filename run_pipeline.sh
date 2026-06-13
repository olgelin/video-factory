#!/bin/bash
cd /e/Hermes-Agent/workspace/xiaoshan/video-factory

# Load API key from .env file
export VF_API_KEY=*** '^.*VF_API_KEY=*** ' video-factory-clawhub/.env | head -1 | cut -d'=' -f2 | tr -d '\r\n')

echo "Key loaded: ${VF_API_KEY:0:10}..."

python -u main_full.py "$@"
