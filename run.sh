#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "/Users/win/Library/Mobile Documents/com~apple~CloudDocs/code/youtube-bgm-auto"

# 前回実行から48時間経過しているか確認
LAST_RUN_FILE=".last_upload"
if [ -f "$LAST_RUN_FILE" ]; then
    LAST_RUN=$(cat "$LAST_RUN_FILE")
    NOW=$(date +%s)
    DIFF=$(( NOW - LAST_RUN ))
    if [ $DIFF -lt 172800 ]; then
        echo "$(date): Skipping — last upload was $(( DIFF / 3600 ))h ago (interval: 48h)"
        exit 0
    fi
fi

# ネットワーク接続を確認（最大3分待機）
echo "$(date): Waiting for network..."
for i in $(seq 1 18); do
    if curl -s --max-time 5 https://oauth2.googleapis.com > /dev/null 2>&1; then
        echo "$(date): Network ready."
        break
    fi
    echo "$(date): Network not ready, retrying in 10s... ($i/18)"
    sleep 10
done

# 実行時刻を記録
date +%s > "$LAST_RUN_FILE"

source venv/bin/activate
python3 main.py
