#!/bin/bash
cd /e/Hermes-Agent/workspace/xiaoshan/video-factory

# Read API key from .env file
export VF_API_KEY=$(grep '^VF_API_KEY=' video-factory-clawhub/.env | cut -d'=' -f2 | tr -d '\r\n')

echo "Key loaded: ${VF_API_KEY:0:10}..."
echo "Running steps $1-$2..."
echo "Topic: $3"

python -u main_full.py --topic "$3" --steps "$1-$2"
