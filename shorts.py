"""
YouTube Shorts 自動生成・投稿:
- 縦型フォーマット（1080x1920）で60秒動画を生成
- Pixabay写真を背景に使用
- #Shorts タグで投稿
- 週3回（月・水・金）自動実行
"""
import os
import subprocess
import random
import io
import json
import logging
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from generate import SOUNDS, _fetch_photo
from upload import upload_video, get_authenticated_service
from playlists import add_to_playlist
from x_post import post_shorts_tweet

TMP_DIR   = os.path.join(os.path.dirname(__file__), "tmp")
W, H      = 1080, 1920   # 縦型
DURATION  = 59            # 60秒未満

# Shorts用タイトルテンプレート
SHORTS_TITLES = {
    "white":        "Pure White Noise 🤍 | 60 Seconds to Fall Asleep #Shorts",
    "pink":         "Pink Noise 🌸 | Soft Sound for Deep Sleep #Shorts",
    "brown":        "Brown Noise 🟫 | The Sound That Quiets Everything #Shorts",
    "rain_light":   "Gentle Rain on Window 🌧 | Instant Calm #Shorts",
    "rain_heavy":   "Heavy Rain Sound ⛈ | Block Out Noise Instantly #Shorts",
    "thunderstorm": "Thunder & Rain ⚡ | Powerful Sleep Sound #Shorts",
    "rain_roof":    "Rain on Rooftop 🏠 | Coziest Sound Ever #Shorts",
    "ocean":        "Ocean Waves 🌊 | 60 Seconds of Pure Relaxation #Shorts",
    "beach":        "Tropical Beach 🏖 | Instant Vacation Vibes #Shorts",
    "river":        "Mountain River 🏞 | The Most Calming Sound #Shorts",
    "waterfall":    "Waterfall Sound 💧 | Nature's White Noise #Shorts",
    "forest":       "Forest Ambiance 🌲 | Escape to Nature #Shorts",
    "city":         "City Ambiance 🌆 | Urban Focus Sound #Shorts",
    "paris":        "Paris Street Café ☕🗼 | Study in France #Shorts",
    "cafe":         "Coffee Shop Sounds ☕ | Focus in 60 Seconds #Shorts",
    "library":      "Quiet Library 📚 | Instant Focus Sound #Shorts",
    "fan":          "Electric Fan 🌀 | Gentle White Noise for Sleep #Shorts",
    "airplane":     "Airplane Cabin 🛫 | The Sound That Knocks You Out #Shorts",
    "train":        "Train Journey 🚂 | Relaxing Rail Sounds #Shorts",
    "fireplace":    "Crackling Fireplace 🔥 | Coziest 60 Seconds #Shorts",
}

SHORTS_DESCRIPTION = """\
✨ Full 1-hour and 8-hour versions on the channel!

🔔 Subscribe for new sleep & ambient sounds every day.

#sleepsounds #whitenoise #ambientmusic #studymusic #relaxation #sleep #asmr
"""


def _make_shorts_frame(sound: dict) -> str:
    """縦型サムネイル画像を生成してパスを返す。"""
    os.makedirs(TMP_DIR, exist_ok=True)
    img_path = os.path.join(TMP_DIR, f"shorts_frame_{sound['type']}.jpg")

    # 背景写真を取得
    photo = _fetch_photo(sound, seed=random.randint(0, 9))

    if photo:
        # 縦型にクロップ
        pw, ph = photo.size
        target_ratio = W / H
        current_ratio = pw / ph
        if current_ratio > target_ratio:
            new_w = int(ph * target_ratio)
            left = (pw - new_w) // 2
            photo = photo.crop((left, 0, left + new_w, ph))
        else:
            new_h = int(pw / target_ratio)
            top = (ph - new_h) // 2
            photo = photo.crop((0, top, pw, top + new_h))
        bg = photo.resize((W, H), Image.LANCZOS)
        # ブラー＋暗め
        bg = bg.filter(ImageFilter.GaussianBlur(radius=3))
    else:
        bg = Image.new("RGB", (W, H), (20, 20, 30))

    # 暗いオーバーレイ
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 160))
    base = bg.convert("RGBA")
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)

    # フォント
    try:
        font_xl = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 90)
        font_lg = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 52)
        font_sm = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 38)
    except Exception:
        font_xl = font_lg = font_sm = ImageFont.load_default()

    # メインテキスト（中央）
    label = sound.get("subtitle", sound["label"])
    lines = label.split()
    # 2行に折り返し
    mid = len(lines) // 2
    line1 = " ".join(lines[:mid]) if mid > 0 else label
    line2 = " ".join(lines[mid:]) if mid > 0 else ""

    cx = W // 2
    cy = H // 2 - 80
    draw.text((cx, cy - 55), line1, font=font_xl, fill="white", anchor="mm",
              stroke_width=3, stroke_fill=(0, 0, 0, 200))
    if line2:
        draw.text((cx, cy + 55), line2, font=font_xl, fill="white", anchor="mm",
                  stroke_width=3, stroke_fill=(0, 0, 0, 200))

    # サブテキスト
    draw.text((cx, cy + 150), "🎧 Listen with headphones or speaker",
              font=font_sm, fill=(220, 220, 220), anchor="mm")

    # 登録ボタン風バナー（下部）
    banner_y = H - 260
    draw.rounded_rectangle([(80, banner_y), (W - 80, banner_y + 160)],
                           radius=30, fill=(0, 0, 0, 180))
    draw.text((cx, banner_y + 45), "🔔 Subscribe for daily sleep sounds",
              font=font_lg, fill=(255, 220, 80), anchor="mm",
              stroke_width=1, stroke_fill=(0, 0, 0, 200))
    draw.text((cx, banner_y + 110), "▶ Full 1h & 8h versions on channel",
              font=font_sm, fill=(200, 230, 255), anchor="mm")

    # Shortsバッジ
    draw.rectangle([(W - 220, 60), (W - 30, 130)], fill=(255, 0, 0))
    draw.text((W - 125, 95), "#Shorts", font=font_sm, fill="white", anchor="mm")

    base.convert("RGB").save(img_path, quality=95)
    return img_path


def generate_short(sound: dict, output_path: str):
    """59秒の縦型Shorts動画を生成する。"""
    frame_path = _make_shorts_frame(sound)
    fade_out_start = max(DURATION - 3, 0)
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", frame_path,
        "-f", "lavfi", "-i", sound["ffmpeg_src"],
        "-t", str(DURATION),
        "-vf", f"scale={W}:{H}",
        "-af", f"afade=t=in:st=0:d=1.5,afade=t=out:st={fade_out_start}:d=3,alimiter=limit=0.95",
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    os.remove(frame_path)


def post_short(sound: dict | None = None):
    """Shorts動画を生成してアップロードする。"""
    os.makedirs(TMP_DIR, exist_ok=True)

    if sound is None:
        # アップロード済みショーツ履歴を読んで重複を避ける
        shorts_history_file = os.path.join(os.path.dirname(__file__), "shorts_history.json")
        if os.path.exists(shorts_history_file):
            with open(shorts_history_file) as f:
                recent = json.load(f)
        else:
            recent = []
        candidates = [s for s in SOUNDS if s["type"] not in recent[-10:]]
        if not candidates:
            candidates = SOUNDS
        sound = random.choice(candidates)
        recent.append(sound["type"])
        with open(shorts_history_file, "w") as f:
            json.dump(recent[-20:], f)

    video_path = os.path.join(TMP_DIR, f"short_{sound['type']}.mp4")
    title       = SHORTS_TITLES.get(sound["type"],
                  f"{sound['label']} 🎵 | 60 Seconds of Calm #Shorts")

    logging.info(f"[Shorts] Generating: {sound['label']}")
    generate_short(sound, video_path)

    meta = {
        "title":       title,
        "description": SHORTS_DESCRIPTION,
        "tags":        ["shorts", "sleepsounds", "whitenoise", "relax",
                        "ambientmusic", "studymusic", "sleep", sound["type"]],
        "categoryId":  "22",
    }

    logging.info(f"[Shorts] Uploading: {title}")
    youtube = get_authenticated_service()
    video_id = upload_video(video_path, None, meta)
    add_to_playlist(youtube, video_id, sound["type"])
    logging.info(f"[Shorts] Done: https://www.youtube.com/watch?v={video_id}")
    post_shorts_tweet(title, video_id)

    if os.path.exists(video_path):
        os.remove(video_path)

    return video_id


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    post_short()
