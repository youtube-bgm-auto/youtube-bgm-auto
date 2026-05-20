#!/bin/bash
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd "/Users/win/Library/Mobile Documents/com~apple~CloudDocs/code/youtube-bgm-auto"
source venv/bin/activate
python3 fantasy_upload.py
