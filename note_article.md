# Pythonで環境音YouTubeチャンネルを全自動化した話【ソースコード付き】

---

## 【無料部分】

### はじめに

「寝ながら稼げるYouTubeチャンネルを自動化できないか」と思い立ち、Pythonで環境音の自動生成・自動投稿システムを作りました。

結果として、**Macが起動しているだけで毎日動画が生成・投稿され続けるシステム**が完成しました。コードの総量は約2,000行。環境音の生成からYouTubeへのアップロード、サムネイル作成、プレイリスト管理、コメント自動返信、アナリティクス取得まで全自動です。

実際に稼働中のチャンネルはこちら：**@SleepScapeDaily**

### 作ったシステムの概要

```
毎日9時（自動起動）
  ↓
音源の種類をランダム選択（28種類）
  ↓
ffmpegで1時間・8時間の動画を生成
  ↓
Pixabay APIで背景動画を取得・合成
  ↓
DALL-E 3 or Pixabayでサムネイル生成
  ↓
YouTube APIで自動アップロード
  ↓
プレイリストに自動振り分け
```

週1回のアナリティクス取得、毎日のコメント自動返信も動いています。

### 対応している音源（28種類）

白色ノイズ、ピンクノイズ、ブラウンノイズ、雨音（弱・強）、雷雨、屋根に当たる雨、海波、ビーチ、川、滝、森、暖炉、カフェ、図書館、パリのカフェ、都市の雑踏、飛行機内、電車、扇風機、ファンタジー系（Wizarding Library、Medieval Tavern、Dragon's Caveなど）

### 月々のランニングコスト

| サービス | 用途 | 費用 |
|---|---|---|
| Pixabay API | 背景画像・動画 | **無料** |
| YouTube Data API | 動画アップロード | **無料**（割当あり） |
| OpenAI API（DALL-E 3） | ファンタジーサムネイル | 1枚約6円 |
| OpenAI API（GPT-4o） | コメント返信文生成 | ごく少額 |
| Mac の電気代 | 常時起動 | 数百円程度 |

ファンタジー系以外の動画はOpenAI APIを使わないため、**ほぼ無料で運用できます**。

### 必要なもの

- Mac（launchdによるスケジュール管理を使用。Windowsはタスクスケジューラで代替可能）
- Python 3.10以上
- ffmpeg（Homebrewでインストール）
- 各種APIキー（取得方法は有料部分で詳しく説明）
  - YouTube Data API（Google Cloud Console）
  - Pixabay API
  - OpenAI API（ファンタジーサムネイルを使う場合のみ）

### GitHubリポジトリ

ソースコード一式はこちら（公開予定）：
`https://github.com/[USERNAME]/youtube-bgm-auto`

---

## 【有料部分】※以下 3,000円

---

### 第1章：環境構築

#### 1-1. ffmpegのインストール

音声・動画の生成にffmpegを使います。macOSではHomebrewから一発で入ります。

```bash
# Homebrewがない場合はまず入れる
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# ffmpegをインストール
brew install ffmpeg

# 確認
ffmpeg -version
```

#### 1-2. Pythonの仮想環境を作る

システム全体を汚さないよう、プロジェクト専用の仮想環境を作ります。

```bash
# プロジェクトフォルダを作成
mkdir youtube-bgm-auto
cd youtube-bgm-auto

# 仮想環境を作成・有効化
python3 -m venv venv
source venv/bin/activate

# 必要なライブラリを一括インストール
pip install google-auth google-auth-oauthlib google-api-python-client \
            Pillow requests openai
```

#### 1-3. GitHubからコードを取得

```bash
git clone https://github.com/[USERNAME]/youtube-bgm-auto .
```

---

### 第2章：APIキーの取得

ここが最初の山場です。3つのサービスに登録が必要です。

#### 2-1. Pixabay API（無料）

1. https://pixabay.com/accounts/register/ でアカウント作成
2. ログイン後 https://pixabay.com/api/docs/ を開く
3. ページ上部に「Your API key:」と表示されているのでコピー
4. プロジェクトの `generate.py` の先頭の `PIXABAY_KEY = "..."` に貼り付ける

```python
# generate.py の1行目付近
PIXABAY_KEY = "ここにPixabay APIキーを貼り付け"
```

#### 2-2. YouTube Data API ＋ OAuth認証（無料・最重要）

YouTubeへのアップロードには、Googleのアカウント認証が必要です。手順が多いですが一度やれば終わりです。

**① Google Cloud Consoleでプロジェクトを作成**

1. https://console.cloud.google.com/ にアクセス（Googleアカウントでログイン）
2. 上部の「プロジェクトを選択」→「新しいプロジェクト」
3. プロジェクト名を入力（例：`youtube-bgm-auto`）→「作成」

**② YouTube Data API v3 を有効化**

1. 左メニュー「APIとサービス」→「ライブラリ」
2. 「YouTube Data API v3」を検索→「有効にする」

**③ OAuth同意画面の設定**

1. 「APIとサービス」→「OAuth同意画面」
2. ユーザーの種類：「外部」を選択→「作成」
3. アプリ名（任意）、メールアドレスを入力→「保存して次へ」
4. スコープ画面：「スコープを追加または削除」→「YouTube」を検索し `.../auth/youtube` と `.../auth/youtube.upload` にチェック→「更新」→「保存して次へ」
5. テストユーザー画面：「+ADD USERS」で自分のGmailアドレスを追加→「保存して次へ」

> ⚠️ **重要：** テストユーザーに追加するのは、動画を投稿したいYouTubeチャンネルと紐づいているGoogleアカウントのメールアドレスです。

**④ OAuth 2.0 クライアントIDを作成**

1. 「APIとサービス」→「認証情報」→「認証情報を作成」→「OAuthクライアントID」
2. アプリケーションの種類：「デスクトップアプリ」
3. 名前：任意（例：`bgm-uploader`）→「作成」
4. ダウンロードボタンをクリック→JSONファイルをダウンロード
5. ファイル名を `client_secret.json` に変更してデスクトップに置く

> ℹ️ **注意：** Google Cloud Consoleのインターフェースが変わり、新しいUI（Google Auth Platform）ではJSONダウンロードボタンが表示されないことがあります。その場合は「認証情報を作成」から新しいOAuthクライアントIDを作り直すとダウンロード画面が出ます。

**⑤ upload.py のパスを確認**

```python
# upload.py の先頭付近
CLIENT_SECRET = os.path.join(os.path.dirname(__file__), "client_secret.json")
```

デスクトップ以外に置く場合はパスを変更してください。

**⑥ 初回認証**

```bash
source venv/bin/activate
python3 -c "from upload import get_authenticated_service; get_authenticated_service()"
```

ブラウザが開いてGoogleのログイン画面が出ます。チャンネルのアカウントでログインして許可すると、`token.pickle` というファイルが生成されます。次回以降はこのファイルを使って自動ログインします。

> ⚠️ `token.pickle` はアクセストークンが入った重要なファイルです。GitHubに上げないよう `.gitignore` に追加してください。

#### 2-3. OpenAI API（ファンタジーサムネイルを使う場合のみ）

1. https://platform.openai.com/ でアカウント作成
2. 「Billing」からクレジットカードを登録して最低5ドルチャージ
3. 「API keys」→「Create new secret key」でキーを生成
4. プロジェクトフォルダに `.env` ファイルを作成して保存：

```
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
```

> ℹ️ ファンタジー系の音源（Wizarding Library等）を使わない場合はOpenAI APIは不要です。PixabayとPillowだけでサムネイルを生成します。

---

### 第3章：システムの設定と動作確認

#### 3-1. 設定ファイルの確認

```python
# generate.py の先頭
PIXABAY_KEY = "あなたのPixabay APIキー"
```

#### 3-2. テスト実行

いきなりアップロードせず、動画生成だけをテストします。

```bash
source venv/bin/activate

python3 -c "
from generate import pick_sound, generate_video, generate_thumbnail
import os

os.makedirs('tmp', exist_ok=True)
sound = pick_sound()
print(f'Selected: {sound[\"label\"]}')

generate_video(sound, 'tmp/test.mp4', duration=10)  # 10秒でテスト
print('Video OK')

generate_thumbnail(sound, 'tmp/test_thumb.jpg', photo_seed=0, duration_label='TEST')
print('Thumbnail OK')
"
```

`tmp/test.mp4` と `tmp/test_thumb.jpg` が生成されれば成功です。

#### 3-3. アップロードテスト

```bash
python3 -c "
from generate import pick_sound, generate_video, generate_thumbnail, build_metadata
from upload import upload_video
import os

os.makedirs('tmp', exist_ok=True)
sound = pick_sound()
generate_video(sound, 'tmp/test.mp4', duration=60)  # 1分でテスト
generate_thumbnail(sound, 'tmp/test_thumb.jpg', photo_seed=0, duration_label='TEST')
meta = build_metadata(sound, hours=1)
meta['title'] = '[TEST] ' + meta['title']  # タイトルにTESTをつける

video_id = upload_video('tmp/test.mp4', 'tmp/test_thumb.jpg', meta)
print(f'Uploaded: https://www.youtube.com/watch?v={video_id}')
"
```

YouTube Studioで確認してテスト動画を削除すれば完了です。

---

### 第4章：自動実行の設定（macOS launchd）

毎日指定した時間に自動で動くよう設定します。

#### 4-1. run.sh の作成

```bash
#!/bin/bash
# プロジェクトのパスを自分の環境に合わせる
PROJECT_DIR="/Users/あなたのユーザー名/youtube-bgm-auto"
LAST_UPLOAD="$PROJECT_DIR/.last_upload"

# 48時間チェック（2日に1回アップロード）
if [ -f "$LAST_UPLOAD" ]; then
    LAST=$(cat "$LAST_UPLOAD")
    NOW=$(date +%s)
    DIFF=$((NOW - LAST))
    if [ $DIFF -lt 172800 ]; then
        echo "Skipped: last upload was $(($DIFF/3600))h ago"
        exit 0
    fi
fi

cd "$PROJECT_DIR"
source venv/bin/activate
python3 main.py
echo $(date +%s) > "$LAST_UPLOAD"
```

```bash
chmod +x run.sh
```

#### 4-2. plistファイルの作成

`~/Library/LaunchAgents/com.bgm.uploader.plist` を作成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bgm.uploader</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/あなたのユーザー名/youtube-bgm-auto/run.sh</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/あなたのユーザー名/youtube-bgm-auto/run.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/あなたのユーザー名/youtube-bgm-auto/run.log</string>
</dict>
</plist>
```

```bash
# 登録
launchctl load ~/Library/LaunchAgents/com.bgm.uploader.plist
```

これで毎日9時に自動実行されます。

---

### 第5章：カスタマイズ

#### 5-1. 音源の追加・削除

`generate.py` の `SOUNDS` リストを編集します。

```python
SOUNDS = [
    {
        "type":       "white",          # 内部識別子（英数字）
        "label":      "White Noise",    # 表示名
        "subtitle":   "Pure White Noise",
        "ffmpeg_src": "anoisesrc=color=white",  # ffmpeg音源フィルター
        "pixabay":    "white minimal abstract",  # Pixabay検索キーワード
    },
    # ... 他の音源
]
```

ffmpegの `anoisesrc` フィルターの `color` パラメーター：
- `white`：白色ノイズ（シャー）
- `pink`：ピンクノイズ（サー、柔らかめ）
- `brown`：ブラウンノイズ（ゴー、低め）

雨音など自前のwavファイルを使う場合：
```python
"ffmpeg_src": "/path/to/rain.wav"
```

#### 5-2. 投稿頻度の変更

`run.sh` の `172800`（秒）を変更します：
- 毎日：`86400`
- 2日ごと：`172800`
- 3日ごと：`259200`

#### 5-3. タイトル・タグのカスタマイズ

`generate.py` の `TITLE_TEMPLATES` と `build_metadata` 関数を編集します。

```python
TITLE_TEMPLATES = {
    "white": "Pure White Noise {d} 🤍 | Fall Asleep Fast | Baby Sleep",
    "rain_light": "Gentle Rain Sounds {d} 🌧 | Sleep & Relaxation",
    # {d} に "1 Hour" や "8 Hours" が入る
}
```

#### 5-4. Shorts の有効化

```bash
# plistを作成して登録（毎朝8時に実行）
# com.bgm.shorts.plist を同様に作成
launchctl load ~/Library/LaunchAgents/com.bgm.shorts.plist
```

---

### 第6章：よくあるエラーと対処法

#### 「invalid_grant: Token has been expired or revoked」

OAuthトークンが切れています。

```bash
rm token.pickle
python3 -c "from upload import get_authenticated_service; get_authenticated_service()"
```

ブラウザで再認証してください。

#### 「FileNotFoundError: client_secret.json」

`client_secret.json` が見つかりません。Google Cloud Consoleから再ダウンロードしてプロジェクトフォルダに置いてください。

#### 「ffmpeg: command not found」

ffmpegがインストールされていません。

```bash
brew install ffmpeg
```

#### Pixabay画像が取得できない

APIキーを確認してください。無料プランでは1時間あたりのリクエスト上限があります。エラーが出ても黒背景でフォールバックするので動画生成は止まりません。

#### アップロードはできるがサムネイルが設定できない

YouTubeアカウントの「電話番号による本人確認」が完了していないと、サムネイルのカスタム設定ができません。YouTube Studioの設定から確認してください。

#### launchdが動かない

macOSがスリープしているとlaunchdは起動しません。「システム設定」→「電源」→「スリープさせない」または「スケジュール」で対処してください。

---

### 第7章：実際の運用で気づいたこと

#### コストについて

ファンタジーサムネイルはDALL-E 3を使いますが、1回の動画生成（1時間版＋8時間版）で2枚生成するため約12円かかります。2日ごとに投稿すると月180円程度です。通常の環境音はPixabay（無料）だけなので費用ゼロです。

#### 同時実行に注意

launchdのジョブが重複して実行されないよう気をつけてください。1時間の動画を生成してアップロードするのに、環境によっては30〜60分かかります。

#### YouTube APIのクォータ

YouTube Data APIには1日あたりの無料枠（10,000ユニット）があります。動画1本のアップロードは約1,600ユニット消費します。1日2〜3本が安全な上限です。

#### token.pickleの有効期限

OAuth tokenは定期的に切れます（数ヶ月ごと）。launchdのログ（`run.log`）を時々確認して、`invalid_grant` エラーが出たら再認証してください。

---

### おわりに

このシステムを作ったことで、「Pythonが書ければYouTubeチャンネルの運営を自動化できる」ということが実証できました。

環境音チャンネル自体の収益化は時間がかかりますが、このシステムを応用すれば他のジャンルにも展開できます。コードを読んでカスタマイズしながら、ぜひ自分だけのチャンネルを育ててみてください。

質問はコメントかTwitter（@[ハンドル]）まで。

---

**ソースコード：** https://github.com/[USERNAME]/youtube-bgm-auto  
**実際のチャンネル：** https://www.youtube.com/@SleepScapeDaily
