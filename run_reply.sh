#!/bin/bash
cd "/Users/win/Library/Mobile Documents/com~apple~CloudDocs/code/youtube-bgm-auto"

# ネットワーク確認
for i in $(seq 1 18); do
    if curl -s --max-time 5 https://oauth2.googleapis.com > /dev/null 2>&1; then
        break
    fi
    sleep 10
done

source venv/bin/activate
python3 auto_reply.py
