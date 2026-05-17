# プログラミング知識ゼロからClaude Codeと一緒にPythonで全自動YouTubeチャンネルを作った話【ソースコード付き】

---

## 【無料部分】

### はじめに

「プログラミングの知識がほとんどなくても、AIと一緒ならYouTubeチャンネルを全自動化できるのか」と思い立ち、**Claude Code**（AnthropicのAIコーディングツール）を使いながらPythonで環境音の自動生成・投稿システムを作りました。

正直に言うと、コードの大部分はClaudeが書いています。自分がやったのは「何を作るか決める」「動作確認する」「こう直してと指示する」の繰り返しです。それでも**Macが起動しているだけで毎日動画が生成・投稿され続けるシステム**が完成しました。総コード量は約2,000行。環境音の生成からYouTubeへのアップロード、サムネイル作成、プレイリスト管理、コメント自動返信、アナリティクス取得まで全自動です。

この記事は「AIと一緒に作る」プロセスで実際に動いたものをそのまま公開します。プログラミング経験がなくても再現できるよう書きました。

実際に稼働中のチャンネルはこちら：**SleepScape**（@SleepScapeDaily）※英語チャンネル

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

- **Claude Code**（claude.ai/code）※このシステムを作るのに使ったAIツール。有料プランが必要
- Mac（launchdによるスケジュール管理を使用。Windowsはタスクスケジューラで代替可能）
- Python 3.10以上
- ffmpeg（Homebrewでインストール）
- 各種APIキー（取得方法は有料部分で詳しく説明）
  - YouTube Data API（Google Cloud Console）
  - Pixabay API
  - OpenAI API（ファンタジーサムネイルを使う場合のみ）

> ℹ️ **Claude Codeについて**  
> ターミナル上で動くAIコーディングツールです。「〇〇という機能を追加して」「このエラーを直して」と日本語で指示するだけでコードを書いてくれます。このシステムは筆者がClaude Codeに指示しながら作りました。コード自体を一から理解しなくても動かせます。

### GitHubリポジトリ

ソースコード一式はこちら：
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

### 第8章：Amazonアフィリエイトで説明欄から収益を得る

YouTube広告収益化（1,000人登録・4,000時間視聴）に到達するまでの間も、説明欄にAmazonアフィリエイトリンクを貼ることで収益を得られます。環境音チャンネルはホワイトノイズマシンや睡眠グッズとの相性が非常に高く、CPMも悪くありません。

#### 8-1. Wiseアカウントを作る（海外送金受け取り用）

Amazon.comのアフィリエイト報酬はUSDで支払われます。日本の銀行口座でも受け取れますが、手数料が高いため**Wise**（旧TransferWise）の利用を強くおすすめします。

1. https://wise.com/jp/ でアカウントを作成
2. 本人確認（マイナンバーカードまたはパスポート）を完了
3. 「残高を追加」→「USD口座を開設」→ **ルーティング番号とアカウント番号**をメモしておく

> ℹ️ Wiseは米国の銀行口座番号（ABA/ルーティング番号）を発行してくれるため、Amazon.comが「米国の銀行口座」として認識します。登録時にこの番号を使います。

#### 8-2. Amazon Associates（Amazon.com）に登録する

1. https://affiliate-program.amazon.com/ にアクセス
2. 「Sign up」→ Amazonアカウント（なければ新規作成）でログイン
3. **アカウント情報**を入力
   - 氏名・住所（日本の住所でOK）
   - 支払い先：「Direct Deposit」を選択 → WiseのUSD口座のルーティング番号とアカウント番号を入力
4. **ウェブサイト・アプリ情報**を入力
   - 「Add a Website or Mobile App」にYouTubeチャンネルのURLを入力
   - 例：`https://www.youtube.com/@SleepScapeDaily`
5. **トラフィックとマネタイズ**の質問に答える（どんなコンテンツか、どう宣伝するかなど。英語ですが素直に答えればOK）
6. **Associate ID（アフィリエイトタグ）**が発行される（例：`yourname-20`）

> ⚠️ 登録後180日以内に3件の売上がないとアカウントが停止されます。まず家族や友人にテスト購入してもらうか、自分でリンク経由で購入するのが確実です。

#### 8-3. SiteStripeでショートリンクを生成する

登録が完了するとAmazon.comを開いたときに画面上部に**SiteStripe**バーが表示されます。

1. Amazon.comで商品ページを開く（例：LectroFan白色ノイズマシンを検索）
2. 画面上部のSiteStripeバーにある「**Short Link**」をクリック
3. `https://amzn.to/XXXXXXX` 形式のURLが生成されるのでコピー

これだけです。このURLにアクセスした人が24時間以内にAmazonで何かを購入すると報酬が発生します（紹介した商品以外でも対象）。

#### 8-4. YouTubeの説明欄に貼る

本システムでは `generate.py` の `AFFILIATE_LINKS` 辞書にリンクを登録するだけで、新規動画に自動的に挿入されます。

```python
# generate.py
AFFILIATE_LINKS = {
    "default": """\
🛒 Recommended for better sleep:
🔊 White Noise Machine → https://amzn.to/XXXXXXX
🎧 Sleep Headphones → https://amzn.to/XXXXXXX
...""",
    "rain": "...",
    "fireplace": "...",
    "nature": "...",
}
```

既存動画への一括追加はYouTube APIで自動処理できます（本記事のコードに含まれています）。

> ⚠️ **必ずアフィリエイト開示を入れること**  
> FTCのガイドラインにより、アフィリエイトリンクを含む場合は開示が必要です。本システムでは説明欄に自動的に以下を挿入しています：  
> `*As an Amazon Associate I earn from qualifying purchases.`

#### 8-5. 音源別おすすめ商品カテゴリ

どの商品を紹介するかで報酬が変わります。「視聴者がその動画を再生しながら何をしているか」を考えると選びやすいです。

| 音源タイプ | おすすめカテゴリ | 選定理由 |
|---|---|---|
| ホワイト・ピンク・ブラウンノイズ | ホワイトノイズマシン、睡眠用Bluetoothヘッドホン、遮光アイマスク、枕スピーカー | 睡眠・集中目的の視聴者が多く、そのまま購買につながりやすい |
| 雨音・雷雨 | レインサウンドマシン、加湿器 | 「雨音で眠りたい」層は快眠グッズへの関心が高い |
| 暖炉・焚き火 | 暖炉映像DVD、キャンドル、アロマディフューザー | 雰囲気・インテリア重視の視聴者、単価が高め |
| 自然音（森・川・海・滝） | 防水Bluetoothスピーカー、ヨガマット | アウトドア・バスタイム・ワークアウト用途 |
| ファンタジー系 | D&Dルールブック、ダイスセット、RPGサプリメント | TRPGセッションBGMとして使うユーザー層が多い |
| カフェ・図書館 | ノイズキャンセリングイヤホン、集中用デスクライト | 勉強・作業用途の視聴者、学生層に強い |

実際に私が使っているリンクの一例（SleepScapeチャンネルの場合）：

🔊 White Noise Machine → https://amzn.to/3R3qsMx  
🎧 Sleep Headphones (Bluetooth) → https://amzn.to/4fjALG3  
😴 Blackout Sleep Mask → https://amzn.to/42CF7Rg  
🔈 Pillow Speaker → https://amzn.to/4doJIvg  
🌧️ Rain Sound Machine → https://amzn.to/3QYw0bb  
🔥 Fireplace DVD → https://amzn.to/4npvJd8  
🌿 Waterproof Bluetooth Speaker → https://amzn.to/4tvbZWX  
🐉 D&D Monster Manual (Rulebook) → https://amzn.to/4nyf7Ak  

> ℹ️ これらは私のアフィリエイトリンクです。ご自身のAssociate IDで同じ商品のリンクを生成して使用してください。

---

### おわりに

このシステムを作ったことで、「プログラミングの知識がなくてもClaude Codeと一緒に動くものを作れる」ということが実証できました。

コードを完全に理解しているわけではありません。それでも動いています。何かエラーが出たらClaude Codeに貼り付けて「直して」と言えばほとんど解決します。この開発体験自体がAI時代のものづくりの一形態だと思っています。

環境音チャンネル自体の収益化は時間がかかりますが、このシステムを応用すれば他のジャンルにも展開できます。ぜひClaude Codeと一緒に自分だけのチャンネルを育ててみてください。

質問はコメントまで。

---

**ソースコード：** https://github.com/[USERNAME]/youtube-bgm-auto  
**実際のチャンネル：** https://www.youtube.com/@SleepScapeDaily
