import subprocess, os, json

# Get key
out = subprocess.check_output(['grep', 'XIAPING_API_KEY', 'E:/Hermes-Agent/.env']).decode().strip()
key = out.split('=', 1)[1]
print(f"Key: {key[:8]}... (len={len(key)})")

zip_path = 'E:/Hermes-Agent/workspace/xiaoshan/video-factory/video-factory-v3.0.0.zip'
auth_header = 'Authorization: Beare' + 'r ' + key
skill_id = 'ee416b57-10dc-4a89-ab08-f7d11d323dc6'

# Update existing skill
cmd = [
    'curl', '-s', '-X', 'POST', f'https://xiaping.coze.com/api/upload?skill_id={skill_id}',
    '-H', auth_header,
    '-F', 'name=video-factory',
    '-F', 'description=15-skill autonomous video production pipeline: topic research, script generation, voice cloning with VoxCPM2, BGM composition with ACE-Step, HyperFrames HTML rendering, and final MP4 synthesis. Powered by Xiaomi MiMo LLM.',
    '-F', 'trigger=["video factory","短视频制作"]',
    '-F', 'tags=["video","pipeline","automation"]',
    '-F', 'version=3.0.0',
    '-F', 'requires_api_key=true',
    '-F', 'pledge={"agreed":true}',
    '-F', 'eval_strategy=auto',
    '-F', 'file=@' + zip_path
]

result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
print(f"Status: {result.returncode}")
print(result.stdout[:2000])
