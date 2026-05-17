# Claude Codeと対話しながらYouTube全自動投稿システムを作った話

## はじめに

「プログラミング知識がほとんどない状態でも、Claude Codeと一緒なら実用的なシステムが作れるのか」という実験として、**環境音YouTubeチャンネルの全自動投稿システム**を作りました。

コードの大部分はClaude Codeが書いています。自分がやったのは設計の方向性を決めること、動作確認、「こう直して」と指示することの繰り返しです。結果として約2,000行のPythonコードが完成し、現在も毎日自動で動いています。

実際に稼働中のチャンネル：[@SleepScapeDaily](https://www.youtube.com/@SleepScapeDaily)（英語の環境音チャンネル）

## システム構成

```
毎日9時（macOS launchd で自動起動）
  ↓
音源の種類をランダム選択（28種類）
  ↓
ffmpeg で1時間・8時間の動画を生成
  ↓
Pixabay API で背景動画を取得・合成
  ↓
DALL-E 3 or Pixabay でサムネイル生成（PIL で合成）
  ↓
YouTube Data API v3 で自動アップロード
  ↓
プレイリストに自動振り分け
```

週1回のアナリティクス取得、毎日のコメント自動返信（GPT-4o）も動いています。

## 技術スタック

| 用途 | ツール |
|---|---|
| 音声・動画生成 | ffmpeg（`anoisesrc` フィルター） |
| 画像処理 | Pillow (PIL) |
| 背景素材 | Pixabay API（無料） |
| ファンタジーサムネイル | OpenAI DALL-E 3 |
| コメント返信 | OpenAI GPT-4o |
| YouTube投稿 | YouTube Data API v3 + OAuth2 |
| 自動スケジュール | macOS launchd |

## ファイル構成

```
youtube-bgm-auto/
├── main.py              # メイン処理
├── generate.py          # 音源定義・動画・サムネイル生成（約1,000行）
├── upload.py            # YouTube API認証・アップロード
├── playlists.py         # プレイリスト管理
├── shorts.py            # Shorts生成・投稿
├── fantasy_upload.py    # ファンタジー音源キュー投稿
├── auto_reply.py        # コメント自動返信
├── analytics.py         # アナリティクス取得
└── run.sh               # 48時間チェック付き実行スクリプト
```

## 実装のポイント

### 音声生成（ffmpeg）

環境音はffmpegの `anoisesrc` フィルターで生成しています。

```python
# ホワイトノイズ
"ffmpeg_src": "anoisesrc=color=white"

# ブラウンノイズ（低周波）
"ffmpeg_src": "anoisesrc=color=brown,lowpass=f=500,volume=0.8"

# 雨音（ノイズ＋フィルタリングで近似）
"ffmpeg_src": "anoisesrc=color=pink,highpass=f=300,lowpass=f=8000,volume=1.2"
```

### 背景動画との合成

Pixabay APIから取得した動画をループ再生しながら、音声スペクトラムをオーバーレイしています。

```python
vf = (
    f"[0:v]loop=loop=-1:size=300:start=0,trim=duration={duration},"
    f"scale=1280:720,setsar=1[bg];"
    f"[1:a]showspectrum=s=1280x100:mode=combined:saturation=1.5:"
    f"color=intensity:scale=log[spec];"
    f"[bg][spec]overlay=0:620[v]"
)
```

### OAuth2トークン管理

`token.pickle` でトークンをキャッシュし、期限切れ時は自動リフレッシュします。

```python
if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
elif not creds or not creds.valid:
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
    creds = flow.run_local_server(port=0)
```

### 48時間インターバル制御

launchdは「N日おき」という指定ができないため、シェルスクリプトで制御しています。

```bash
if [ -f "$LAST_UPLOAD" ]; then
    LAST=$(cat "$LAST_UPLOAD")
    NOW=$(date +%s)
    DIFF=$((NOW - LAST))
    if [ $DIFF -lt 172800 ]; then  # 48時間 = 172800秒
        exit 0
    fi
fi
```

## ランニングコスト

| サービス | 費用 |
|---|---|
| Pixabay API | **無料** |
| YouTube Data API | **無料**（1日10,000ユニット） |
| OpenAI DALL-E 3 | 約6円/枚（ファンタジー系のみ） |
| OpenAI GPT-4o | コメント返信に少額 |

通常の環境音はOpenAI APIを使わないため**ほぼ無料**で運用できます。

## Claude Codeとの開発体験

技術的な話ではないですが、このプロジェクトで感じたことを。

エラーが出たらそのままClaude Codeに貼り付けて「直して」と言えばほとんど解決します。「Pixabay APIのレスポンス形式が変わったっぽいので対応して」「token.pickleが切れた時に自動再認証できるようにして」といった自然言語の指示で実装が進みます。

コードを完全に理解しているわけではありません。それでも動いています。「動くものを作る」という目的においては、これで十分だと感じています。

## ソースコード

GitHubで公開しています。

https://github.com/youtube-bgm-auto/youtube-bgm-auto

## セットアップ手順の詳細

APIキーの取得方法・よくあるエラーの対処法・カスタマイズ方法を含む詳細なセットアップ手順はnoteで公開しています。

https://note.com/sleepscapedaily/n/n5b1bda53ba32
