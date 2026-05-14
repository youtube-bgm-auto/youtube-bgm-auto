# YouTube Ambient Sound Channel Automation 🎵

Pythonで環境音YouTubeチャンネルを全自動化するシステムです。
音声生成からYouTubeアップロード・サムネイル作成・プレイリスト管理まで完全自動。

**実際に稼働中のチャンネル → [@SleepScapeDaily](https://www.youtube.com/@SleepScapeDaily)**

---

## 機能

- 🎵 **28種類の環境音を自動生成**（ホワイトノイズ・雨音・焚き火・ファンタジーなど）
- 🎬 **1時間・8時間版を自動生成**（ffmpegによる音声合成＋動画合成）
- 🖼️ **サムネイル自動生成**（Pixabay API + PIL / ファンタジー系はDALL-E 3）
- 📤 **YouTube自動アップロード**（YouTube Data API v3）
- 📋 **プレイリスト自動振り分け**（5カテゴリ）
- 📱 **Shorts自動生成・投稿**（縦型60秒）
- 💬 **コメント自動返信**（GPT-4oで生成）
- 📊 **週次アナリティクスレポート**

## 技術スタック

| 用途 | ツール |
|---|---|
| 音声・動画生成 | ffmpeg |
| 画像処理 | Pillow (PIL) |
| 背景素材 | Pixabay API（無料） |
| ファンタジーサムネイル | OpenAI DALL-E 3 |
| コメント返信 | OpenAI GPT-4o |
| YouTube投稿 | YouTube Data API v3 |
| 自動スケジュール | macOS launchd |

## ファイル構成

```
youtube-bgm-auto/
├── main.py              # メイン処理（動画生成→アップロード）
├── generate.py          # 音源定義・動画・サムネイル生成
├── upload.py            # YouTube API認証・アップロード
├── playlists.py         # プレイリスト管理
├── shorts.py            # Shorts生成・投稿
├── fantasy_upload.py    # ファンタジー音源キュー投稿
├── auto_reply.py        # コメント自動返信
├── analytics.py         # アナリティクス取得
├── run.sh               # 48時間チェック付き実行スクリプト
└── .env                 # APIキー（GitHubに上げない）
```

## セットアップ

詳細なセットアップ手順は **[noteの有料記事](https://note.com/)** を参照してください。

APIキーの取得方法・よくあるエラーの対処法・カスタマイズ方法を網羅しています。

### 簡易手順

```bash
# 1. ffmpegをインストール
brew install ffmpeg

# 2. Python仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 3. ライブラリをインストール
pip install google-auth google-auth-oauthlib google-api-python-client \
            Pillow requests openai

# 4. APIキーを設定
echo "OPENAI_API_KEY=your_key_here" > .env
# generate.py の PIXABAY_KEY も編集

# 5. YouTube OAuth認証（初回のみブラウザが開く）
python3 -c "from upload import get_authenticated_service; get_authenticated_service()"

# 6. テスト実行
python3 main.py
```

## 月々のコスト

| サービス | 費用 |
|---|---|
| Pixabay API | **無料** |
| YouTube Data API | **無料** |
| OpenAI API（ファンタジーサムネイルのみ） | 約数十〜百円/月 |

ファンタジー系音源を使わない場合は**ほぼ無料**で運用できます。

## ライセンス

MIT License

## 作者

[@SleepScapeDaily](https://www.youtube.com/@SleepScapeDaily)
