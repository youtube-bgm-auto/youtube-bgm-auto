import subprocess
import random
import os
import io
import math
from datetime import datetime
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PIXABAY_KEY = "55697844-994066d6d9f510671090a496b"
VIDEO_SIZE = "1920x1080"
VIDEO_W = 1920
VIDEO_H = 1080
VIDEO_FPS = 24

# OpenAI APIキーを.envから読み込む
def _load_openai_key() -> str | None:
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY="):
                    return line.strip().split("=", 1)[1]
    return None

def fetch_background_video(sound: dict, output_path: str, seed: int = 0) -> bool:
    """Pixabayから背景動画をダウンロードしてファイルに保存。成功したらTrueを返す。"""
    query = sound.get("pixabay", "nature landscape peaceful")
    try:
        r = requests.get("https://pixabay.com/api/videos/", params={
            "key": PIXABAY_KEY,
            "q": query,
            "video_type": "film",
            "per_page": 20,
            "safesearch": "true",
        }, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return False

        def video_score(hit: dict) -> int:
            videos = hit.get("videos", {})
            best = max(
                videos.values(),
                key=lambda v: int(v.get("width", 0)) * int(v.get("height", 0)),
                default={},
            )
            pixels = int(best.get("width", 0)) * int(best.get("height", 0))
            duration = int(hit.get("duration", 0))
            return pixels + min(duration, 60) * 10000

        ranked = sorted(hits, key=video_score, reverse=True)
        video = ranked[seed % min(len(ranked), 10)]
        videos = video.get("videos", {})
        # 解像度の高いものを優先
        url = (videos.get("large", {}).get("url") or
               videos.get("medium", {}).get("url") or
               videos.get("small", {}).get("url"))
        if not url:
            return False
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        return True
    except Exception as e:
        print(f"Pixabay video fetch failed: {e}")
        return False


def _fetch_photo(sound: dict, seed: int = 0) -> Image.Image | None:
    query = sound.get("pixabay", "nature landscape peaceful")
    try:
        r = requests.get("https://pixabay.com/api/", params={
            "key": PIXABAY_KEY,
            "q": query,
            "image_type": "photo",
            "orientation": "horizontal",
            "min_width": 1280,
            "per_page": 20,
            "safesearch": "true",
        }, timeout=15)
        r.raise_for_status()
        hits = r.json().get("hits", [])
        if not hits:
            return None
        hits = sorted(
            hits,
            key=lambda h: int(h.get("imageWidth", 0)) * int(h.get("imageHeight", 0)),
            reverse=True,
        )
        photo = hits[seed % min(len(hits), 10)]
        img_url = photo.get("largeImageURL") or photo.get("webformatURL")
        img_r = requests.get(img_url, timeout=30)
        img_r.raise_for_status()
        return Image.open(io.BytesIO(img_r.content)).convert("RGB")
    except Exception as e:
        print(f"Pixabay fetch failed: {e}")
        return None

SOUNDS = [
    # ── ノイズ系 ──────────────────────────────────────────
    {
        "type": "white",
        "label": "White Noise",
        "subtitle": "Pure White Noise",
        "ffmpeg_src": "anoisesrc=color=white",
        "pixabay": "abstract white light minimal",
    },
    {
        "type": "pink",
        "label": "Pink Noise",
        "subtitle": "Soft Pink Noise",
        "ffmpeg_src": "anoisesrc=color=pink",
        "pixabay": "cherry blossom spring pink sunset",
    },
    {
        "type": "brown",
        "label": "Brown Noise",
        "subtitle": "Deep Brown Noise",
        "ffmpeg_src": "anoisesrc=color=brown",
        "pixabay": "autumn forest brown cozy cabin",
    },

    # ── 雨・嵐系 ─────────────────────────────────────────
    {
        "type": "rain_light",
        "label": "Light Rain",
        "subtitle": "Gentle Rain on Window",
        "ffmpeg_src": "anoisesrc=color=pink,lowpass=f=3000,volume=0.9",
        "pixabay": "rain window glass drops city",
    },
    {
        "type": "rain_heavy",
        "label": "Heavy Rain",
        "subtitle": "Heavy Rainstorm",
        "ffmpeg_src": "anoisesrc=color=white,lowpass=f=4000,volume=1.4",
        "pixabay": "heavy rain storm dark night",
    },
    {
        "type": "thunderstorm",
        "label": "Thunderstorm",
        "subtitle": "Thunder and Rain",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=600,volume=1.8",
        "pixabay": "thunderstorm lightning dark dramatic sky",
    },
    {
        "type": "rain_roof",
        "label": "Rain on Roof",
        "subtitle": "Cozy Rain on Rooftop",
        "ffmpeg_src": "anoisesrc=color=white,highpass=f=800,lowpass=f=5000,volume=1.1",
        "pixabay": "cozy cabin rain roof countryside",
    },

    # ── 水・自然系 ────────────────────────────────────────
    {
        "type": "ocean",
        "label": "Ocean Waves",
        "subtitle": "Relaxing Ocean Waves",
        "ffmpeg_src": "anoisesrc=color=pink,lowpass=f=900,highpass=f=40,volume=1.2",
        "pixabay": "ocean waves beach sunset sea",
    },
    {
        "type": "beach",
        "label": "Beach Sounds",
        "subtitle": "Tropical Beach Waves",
        "ffmpeg_src": "anoisesrc=color=pink,lowpass=f=1200,highpass=f=60,volume=1.1",
        "pixabay": "tropical beach blue sea palm",
    },
    {
        "type": "river",
        "label": "River Stream",
        "subtitle": "Mountain River Stream",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=300,lowpass=f=5000,volume=1.0",
        "pixabay": "mountain river stream waterfall nature",
    },
    {
        "type": "waterfall",
        "label": "Waterfall",
        "subtitle": "Peaceful Waterfall",
        "ffmpeg_src": "anoisesrc=color=white,highpass=f=400,lowpass=f=8000,volume=1.2",
        "pixabay": "waterfall jungle green forest nature",
    },
    {
        "type": "forest",
        "label": "Forest Sounds",
        "subtitle": "Peaceful Forest Ambiance",
        "ffmpeg_src": "anoisesrc=color=brown,highpass=f=200,lowpass=f=2000,volume=0.9",
        "pixabay": "forest green trees sunlight peaceful",
    },

    # ── 都市・カフェ系 ─────────────────────────────────────
    {
        "type": "city",
        "label": "City Ambiance",
        "subtitle": "Busy City Sounds",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=150,lowpass=f=3500,volume=1.1",
        "pixabay": "city night urban street lights traffic",
    },
    {
        "type": "paris",
        "label": "Paris Street Café",
        "subtitle": "Paris Street Corner",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=200,lowpass=f=3000,volume=0.9,tremolo=f=1.5:d=0.15",
        "pixabay": "paris cafe street eiffel tower france",
    },
    {
        "type": "cafe",
        "label": "Coffee Shop",
        "subtitle": "Cozy Coffee Shop",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=250,lowpass=f=2800,volume=0.85",
        "pixabay": "coffee shop cafe interior cozy warm",
    },
    {
        "type": "library",
        "label": "Quiet Library",
        "subtitle": "Peaceful Library",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=500,volume=0.4",
        "pixabay": "library books quiet study reading room",
    },

    # ── 機械・室内系 ──────────────────────────────────────
    {
        "type": "fan",
        "label": "Electric Fan",
        "subtitle": "Gentle Electric Fan",
        "ffmpeg_src": "anoisesrc=color=brown,highpass=f=100,lowpass=f=1000,volume=1.0",
        "pixabay": "bedroom interior minimalist cozy night",
    },
    {
        "type": "airplane",
        "label": "Airplane Cabin",
        "subtitle": "Airplane White Noise",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=80,lowpass=f=700,volume=1.3",
        "pixabay": "airplane window clouds sky travel",
    },
    {
        "type": "train",
        "label": "Train Journey",
        "subtitle": "Relaxing Train Sounds",
        "ffmpeg_src": "anoisesrc=color=brown,highpass=f=60,lowpass=f=800,volume=1.2",
        "pixabay": "train window landscape countryside travel",
    },
    {
        "type": "fireplace",
        "label": "Crackling Fireplace",
        "subtitle": "Cozy Fireplace",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=1500,volume=0.9",
        "pixabay": "fireplace cozy fire warm winter cabin",
    },

    # ── ファンタジー・世界観系 ─────────────────────────────────
    {
        "type": "fantasy_library",
        "label": "Wizarding Library",
        "subtitle": "Candlelit Library at Night",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=350,volume=0.35",
        "pixabay": "library candles dark books vintage magic",
    },
    {
        "type": "medieval_tavern",
        "label": "Medieval Tavern",
        "subtitle": "Cozy Medieval Tavern",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=250,lowpass=f=2800,volume=0.9",
        "pixabay": "medieval castle interior fireplace stone",
    },
    {
        "type": "enchanted_forest",
        "label": "Enchanted Forest",
        "subtitle": "Mystical Enchanted Forest",
        "ffmpeg_src": "anoisesrc=color=brown,highpass=f=200,lowpass=f=2500,volume=0.85",
        "pixabay": "fantasy forest magical mist mystical trees",
    },
    {
        "type": "ancient_temple",
        "label": "Ancient Temple",
        "subtitle": "Mysterious Ancient Temple",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=400,volume=0.65",
        "pixabay": "ancient temple ruins stone mystical fog",
    },
    {
        "type": "cozy_cottage",
        "label": "Cozy Fantasy Cottage",
        "subtitle": "Hobbit-Style Cozy Cottage",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=700,lowpass=f=4500,volume=1.0",
        "pixabay": "cozy cottage hobbit house fantasy garden",
    },
    {
        "type": "castle_wind",
        "label": "Castle Ramparts",
        "subtitle": "Windy Castle Ramparts",
        "ffmpeg_src": "anoisesrc=color=white,highpass=f=1500,lowpass=f=8000,volume=0.8",
        "pixabay": "castle ramparts stone wall sky clouds",
    },
    {
        "type": "space_station",
        "label": "Deep Space Station",
        "subtitle": "Sci-Fi Space Station Hum",
        "ffmpeg_src": "anoisesrc=color=pink,highpass=f=60,lowpass=f=500,volume=1.1",
        "pixabay": "space galaxy stars nebula cosmos dark",
    },
    {
        "type": "dragon_cave",
        "label": "Dragon's Cave",
        "subtitle": "Dark Dragon's Cave",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=300,volume=0.7",
        "pixabay": "dark cave underground fantasy stalactite",
    },
    # ── 実録音源 ──────────────────────────────────────
    {
        "type": "train_underpass",
        "label": "Train Underpass",
        "subtitle": "Urban Train Ambiance",
        "ffmpeg_src": "anoisesrc=color=brown,volume=0.5",  # フォールバック用
        "audio_file": os.path.join(os.path.dirname(__file__), "recordings", "電車高架下.m4a"),
        "pixabay": "train station urban city railway",
    },
    {
        "type": "study_hall",
        "label": "Study Hall",
        "subtitle": "Quiet Study Hall Ambiance",
        "ffmpeg_src": "anoisesrc=color=pink,volume=0.5",
        "audio_file": os.path.join(os.path.dirname(__file__), "recordings", "study_hall_anon.m4a"),
        "pixabay": "library study hall university interior",
    },
    {
        "type": "waiting_room",
        "label": "Station Waiting Room",
        "subtitle": "Busy Waiting Room Ambiance",
        "ffmpeg_src": "anoisesrc=color=white,volume=0.5",
        "audio_file": os.path.join(os.path.dirname(__file__), "recordings", "theater_anon.m4a"),
        "pixabay": "train station waiting room interior",
    },
    {
        "type": "night_drive",
        "label": "Night Drive",
        "subtitle": "Relaxing Car Interior Sounds",
        "ffmpeg_src": "anoisesrc=color=brown,lowpass=f=600,volume=0.6",
        "audio_file": os.path.join(os.path.dirname(__file__), "recordings", "休日のバス車内_anon.m4a"),
        "pixabay": "night drive highway car window city lights",
    },
    {
        "type": "electric_fan_real",
        "label": "Electric Fan",
        "subtitle": "Real Electric Fan White Noise",
        "ffmpeg_src": "anoisesrc=color=white,volume=0.5",
        "audio_file": os.path.join(os.path.dirname(__file__), "recordings", "エレクトリックファン_anon.m4a"),
        "pixabay": "electric fan bedroom summer cool",
    },
]


HISTORY_FILE = os.path.join(os.path.dirname(__file__), "history.json")
HISTORY_LIMIT = 33  # 全音源を使い切るまで繰り返さない（28+5録音）


def _load_history() -> list:
    import json
    if os.path.exists(HISTORY_FILE):
        try:
            return json.load(open(HISTORY_FILE))["recent"]
        except Exception:
            pass
    return []


def _save_history(recent: list):
    import json
    with open(HISTORY_FILE, "w") as f:
        json.dump({"recent": recent[-HISTORY_LIMIT:]}, f, indent=2)


_FANTASY_KEYS = {
    "fantasy_library", "medieval_tavern", "enchanted_forest",
    "ancient_temple", "cozy_cottage", "castle_wind",
    "space_station", "dragon_cave",
}

FANTASY_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "fantasy_history.json")


def _load_fantasy_history() -> list:
    import json
    if os.path.exists(FANTASY_HISTORY_FILE):
        try:
            return json.load(open(FANTASY_HISTORY_FILE))["recent"]
        except Exception:
            pass
    return []


def _save_fantasy_history(recent: list):
    import json
    with open(FANTASY_HISTORY_FILE, "w") as f:
        json.dump({"recent": recent[-len(_FANTASY_KEYS):]}, f, indent=2)


def pick_sound(prefer_fantasy: bool = True) -> dict:
    """
    prefer_fantasy=True のとき約50%でファンタジー系を選ぶ。
    ファンタジーは独自の短い履歴（8種サイクル）で管理するため
    非ファンタジーより高頻度で登場する。
    """
    recent_all = _load_history()

    if prefer_fantasy and random.random() < 0.5:
        # ファンタジープール（独自の短い履歴）
        recent_f = _load_fantasy_history()
        f_pool = [s for s in SOUNDS if s["type"] in _FANTASY_KEYS and s["type"] not in recent_f]
        if not f_pool:
            f_pool = [s for s in SOUNDS if s["type"] in _FANTASY_KEYS]
        sound = random.choice(f_pool)
        _save_fantasy_history(recent_f + [sound["type"]])
    else:
        # 非ファンタジープール（既存の全体履歴）
        other_pool = [s for s in SOUNDS if s["type"] not in _FANTASY_KEYS and s["type"] not in recent_all]
        if not other_pool:
            other_pool = [s for s in SOUNDS if s["type"] not in _FANTASY_KEYS]
        sound = random.choice(other_pool)

    recent_all.append(sound["type"])
    _save_history(recent_all)
    return sound


def save_photo_to_file(sound: dict, path: str, seed: int = 0) -> bool:
    """Pixabay写真をファイルに保存。成功したらTrueを返す。"""
    photo = _fetch_photo(sound, seed)
    if photo:
        photo.save(path, quality=90)
        return True
    return False


def _background_filter(is_video: bool) -> str:
    """背景素材を16:9の1080pへクロップし、軽く整える。"""
    filters = [
        f"scale={VIDEO_W}:{VIDEO_H}:force_original_aspect_ratio=increase",
        f"crop={VIDEO_W}:{VIDEO_H}",
        "setsar=1",
    ]
    if is_video:
        filters.append(f"fps={VIDEO_FPS}")
    return ",".join(filters)


def _audio_polish_filter(duration: int, normalize: bool = False) -> str:
    """長尺BGM用に音量を整え、開始・終了のクリックや唐突さを抑える。"""
    filters = []
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    fade_out_start = max(duration - 4, 0)
    filters.extend([
        "afade=t=in:st=0:d=3",
        f"afade=t=out:st={fade_out_start}:d=4",
        "alimiter=limit=0.95",
    ])
    return ",".join(filters)


def generate_video(sound: dict, output_path: str, duration: int = 3600,
                   base_path: str = None, photo_path: str = None):
    """動画を生成する。
    - base_path 指定時: ループコピー（高速・8h用）
    - photo_path 指定時: 写真背景＋波形ビジュアライザー
    - それ以外: 黒画面（フォールバック）
    """
    if base_path and os.path.exists(base_path):
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", base_path,
            "-t", str(duration),
            "-c", "copy",
            "-movflags", "+faststart",
            output_path,
        ]
    elif photo_path and os.path.exists(photo_path):
        # 背景（動画 or 写真）+ スペクトラムビジュアライザー
        is_video = photo_path.endswith(".mp4")
        if is_video:
            input_args = ["-stream_loop", "-1", "-i", photo_path]
        else:
            input_args = ["-loop", "1", "-i", photo_path]
        scale_filter = _background_filter(is_video)

        # 共通エンコード設定（YouTube推奨）
        video_enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                     "-r", str(VIDEO_FPS), "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        audio_enc = ["-c:a", "aac", "-b:a", "256k"]

        audio_file = sound.get("audio_file")
        if audio_file and os.path.exists(audio_file):
            # 実録音: asplitで音声を分岐（スペクトラム用 + 出力用）
            filter_complex = (
                f"[0:v]{scale_filter},boxblur=1:1[bg];"
                "[bg]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.25:t=fill[dark];"
                f"[1:a]{_audio_polish_filter(duration, normalize=True)},asplit[aout][aspec];"
                f"[aspec]showspectrum=s={VIDEO_W}x100:slide=scroll:saturation=1.5"
                ":color=intensity:scale=cbrt:overlap=0.5[sp];"
                "[dark][sp]overlay=0:980[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                *input_args,
                "-stream_loop", "-1", "-i", audio_file,
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-map", "[out]", "-map", "[aout]",
                *video_enc, *audio_enc,
                output_path,
            ]
        else:
            # 合成音源: asplitで音声を分岐
            filter_complex = (
                f"[0:v]{scale_filter},boxblur=1:1[bg];"
                "[bg]drawbox=x=0:y=0:w=iw:h=ih:color=black@0.25:t=fill[dark];"
                f"[1:a]{_audio_polish_filter(duration)},asplit[aout][aspec];"
                f"[aspec]showspectrum=s={VIDEO_W}x100:slide=scroll:saturation=1.5"
                ":color=intensity:scale=cbrt:overlap=0.5[sp];"
                "[dark][sp]overlay=0:980[out]"
            )
            cmd = [
                "ffmpeg", "-y",
                *input_args,
                "-f", "lavfi", "-i", sound["ffmpeg_src"],
                "-t", str(duration),
                "-filter_complex", filter_complex,
                "-map", "[out]", "-map", "[aout]",
                *video_enc, *audio_enc,
                output_path,
            ]
    else:
        # フォールバック: 黒背景
        audio_enc = ["-c:a", "aac", "-b:a", "256k"]
        audio_file = sound.get("audio_file")
        if audio_file and os.path.exists(audio_file):
            audio_filter = _audio_polish_filter(duration, normalize=True)
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=black:s={VIDEO_SIZE}:r=1",
                "-stream_loop", "-1", "-i", audio_file,
                "-t", str(duration),
                "-af", audio_filter,
                "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                *audio_enc,
                "-movflags", "+faststart",
                output_path,
            ]
        else:
            audio_filter = _audio_polish_filter(duration)
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"color=black:s={VIDEO_SIZE}:r=1",
                "-f", "lavfi", "-i", sound["ffmpeg_src"],
                "-t", str(duration),
                "-af", audio_filter,
                "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
                *audio_enc,
                "-movflags", "+faststart",
                output_path,
            ]
    subprocess.run(cmd, check=True)


# ---------- landscape painters ----------

def _gradient(img, top, bottom):
    draw = ImageDraw.Draw(img)
    h = img.height
    for y in range(h):
        t = y / h
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(0, y), (img.width, y)], fill=(r, g, b))


def _mountain_silhouette(draw, w, h, peaks, color, y_base):
    pts = [(0, h)]
    for i, (px, py) in enumerate(peaks):
        if i == 0:
            pts += [(0, y_base), (px, py)]
        else:
            prev_px = peaks[i - 1][0]
            mx = (prev_px + px) // 2
            pts.append((mx, y_base))
            pts.append((px, py))
    pts += [(w, y_base), (w, h)]
    draw.polygon(pts, fill=color)


def _stars(draw, w, h, count, seed=42):
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, int(h * 0.55))
        r = rng.choice([1, 1, 1, 2])
        br = rng.randint(180, 255)
        draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=(br, br, br))


def _moon(draw, cx, cy, r, color=(255, 250, 220)):
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill=color)
    draw.ellipse([(cx + r // 4, cy - r), (cx + r // 4 + int(r * 1.6), cy + int(r * 0.6))],
                 fill=None)


def _water_reflection(draw, w, y_start, h, base_color, seed=7):
    rng = random.Random(seed)
    for y in range(y_start, h, 3):
        t = (y - y_start) / max(h - y_start, 1)
        r = int(base_color[0] * (1 - t * 0.3))
        g = int(base_color[1] * (1 - t * 0.2))
        b = int(base_color[2] * (1 - t * 0.1))
        for _ in range(rng.randint(2, 5)):
            x = rng.randint(0, w)
            lw = rng.randint(8, 60)
            draw.line([(x, y), (x + lw, y)], fill=(r, g, b), width=2)


def _rain_streaks(draw, w, h, count, seed=3):
    rng = random.Random(seed)
    for _ in range(count):
        x = rng.randint(0, w)
        y = rng.randint(0, h)
        length = rng.randint(15, 45)
        alpha = rng.randint(60, 150)
        draw.line([(x, y), (x - 6, y + length)], fill=(180, 210, 240), width=1)


def _tree_silhouette(draw, cx, base_y, height, spread, color):
    draw.polygon([
        (cx, base_y - height),
        (cx - spread, base_y),
        (cx + spread, base_y),
    ], fill=color)
    draw.polygon([
        (cx, base_y - height * 0.65),
        (cx - spread * 1.2, base_y - height * 0.25),
        (cx + spread * 1.2, base_y - height * 0.25),
    ], fill=color)
    draw.polygon([
        (cx, base_y - height * 0.9),
        (cx - spread * 0.8, base_y - height * 0.45),
        (cx + spread * 0.8, base_y - height * 0.45),
    ], fill=color)


def _cloud(draw, cx, cy, r, color=(240, 245, 255)):
    for dx, dy, rr in [(-r, 0, r), (0, -int(r*0.7), int(r*0.85)),
                        (r, 0, r), (0, 0, int(r*1.1))]:
        x, y = cx + dx, cy + dy
        draw.ellipse([(x - rr, y - rr), (x + rr, y + rr)], fill=color)


def _cherry_blossoms(draw, cx, base_y, count, seed=1):
    rng = random.Random(seed)
    for _ in range(count):
        x = cx + rng.randint(-160, 160)
        y = base_y + rng.randint(-200, 0)
        r = rng.randint(5, 14)
        alpha = rng.randint(160, 240)
        draw.ellipse([(x-r, y-r), (x+r, y+r)],
                     fill=(255, rng.randint(160, 200), rng.randint(180, 210)))


def _river_curve(draw, w, h, water_top, color):
    pts = []
    for x in range(0, w + 1, 4):
        t = x / w
        y = int(water_top + 60 * math.sin(t * math.pi * 1.5) + (h - water_top) * t * 0.4)
        pts.append((x, y))
    pts += [(w, h), (0, h)]
    draw.polygon(pts, fill=color)


def _paint_white_noise(img):
    w, h = img.size
    _gradient(img, (8, 12, 35), (30, 50, 90))
    draw = ImageDraw.Draw(img)
    _stars(draw, w, h, 220)
    _moon(draw, 980, 110, 70)
    _mountain_silhouette(draw, w, h,
        [(0,480),(180,320),(360,410),(540,260),(720,380),(900,290),(1100,370),(1280,440)],
        (18, 28, 55), 500)
    _mountain_silhouette(draw, w, h,
        [(0,560),(200,430),(450,490),(680,400),(900,460),(1100,420),(1280,500)],
        (12, 20, 42), 580)
    _water_reflection(draw, w, 580, h, (20, 40, 80))
    # 霧
    fog = Image.new("RGBA", (w, 80), (200, 220, 255, 35))
    img.paste(Image.alpha_composite(img.crop((0, 490, w, 570)).convert("RGBA"), fog).convert("RGB"), (0, 490))


def _paint_pink_noise(img):
    w, h = img.size
    _gradient(img, (255, 130, 100), (255, 200, 160))
    draw = ImageDraw.Draw(img)
    # 地面
    draw.rectangle([(0, 520), (w, h)], fill=(80, 50, 40))
    draw.rectangle([(0, 500), (w, 530)], fill=(100, 65, 50))
    # 桜の木
    for cx in [220, 640, 1060]:
        draw.rectangle([(cx-12, 380), (cx+12, 520)], fill=(70, 45, 35))
        _cherry_blossoms(draw, cx, 400, 180, seed=cx)
    # 雲
    for cx, cy in [(200, 100), (600, 80), (1000, 120)]:
        _cloud(draw, cx, cy, 55, (255, 230, 220))
    # 花びら舞う
    rng = random.Random(5)
    for _ in range(60):
        x = rng.randint(0, w)
        y = rng.randint(100, 480)
        r = rng.randint(3, 8)
        draw.ellipse([(x-r, y-r), (x+r, y+r)], fill=(255, 180, 190))


def _paint_brown_noise(img):
    w, h = img.size
    _gradient(img, (15, 8, 5), (50, 28, 10))
    draw = ImageDraw.Draw(img)
    _stars(draw, w, h, 80, seed=99)
    # 森
    _mountain_silhouette(draw, w, h,
        [(0,500),(200,420),(400,460),(600,400),(800,450),(1000,410),(1280,470)],
        (25, 14, 5), 520)
    for cx in range(60, w, 90):
        ht = random.Random(cx).randint(130, 220)
        _tree_silhouette(draw, cx, 530, ht, ht // 4, (18, 10, 4))
    # 焚き火
    fx = 640
    draw.polygon([(fx, 520), (fx-30, 560), (fx+30, 560)], fill=(200, 80, 20))
    draw.polygon([(fx, 510), (fx-18, 545), (fx+18, 545)], fill=(255, 160, 30))
    draw.ellipse([(fx-8, 502), (fx+8, 518)], fill=(255, 220, 80))
    # 月
    draw.ellipse([(860, 60), (940, 140)], fill=(255, 240, 180))


def _paint_rain(img):
    w, h = img.size
    _gradient(img, (18, 22, 40), (40, 55, 80))
    draw = ImageDraw.Draw(img)
    _mountain_silhouette(draw, w, h,
        [(0,420),(300,350),(600,390),(900,330),(1280,400)],
        (25, 32, 55), 440)
    # 湖面
    draw.rectangle([(0, 500), (w, h)], fill=(22, 35, 60))
    _water_reflection(draw, w, 505, h, (30, 55, 100), seed=12)
    # 雨
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    _rain_streaks(od, w, h, 400)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))
    # 波紋
    rng = random.Random(8)
    for _ in range(20):
        x = rng.randint(50, w - 50)
        y = rng.randint(510, h - 20)
        r = rng.randint(6, 22)
        draw.ellipse([(x-r, y-r//3), (x+r, y+r//3)], outline=(80, 120, 180), width=1)


def _paint_river(img):
    w, h = img.size
    _gradient(img, (100, 170, 230), (180, 220, 250))
    draw = ImageDraw.Draw(img)
    # 雲
    for cx, cy in [(180, 90), (640, 60), (1100, 100)]:
        _cloud(draw, cx, cy, 70)
    # 山
    _mountain_silhouette(draw, w, h,
        [(0,360),(200,220),(450,300),(700,200),(950,280),(1150,230),(1280,310)],
        (60, 100, 70), 380)
    _mountain_silhouette(draw, w, h,
        [(0,440),(250,360),(550,400),(800,350),(1050,390),(1280,420)],
        (40, 75, 50), 460)
    # 川
    _river_curve(draw, w, h, 430, (60, 150, 200))
    # 川のハイライト
    for i in range(5):
        x = 100 + i * 220
        y = 470 + i * 20
        draw.ellipse([(x, y), (x+60, y+8)], fill=(160, 210, 240))
    # 川岸の石
    rng = random.Random(3)
    for _ in range(18):
        x = rng.randint(0, w)
        y = rng.randint(440, 480)
        r = rng.randint(6, 18)
        draw.ellipse([(x-r, y-r//2), (x+r, y+r//2)], fill=(130, 120, 110))


LANDSCAPE_PAINTERS = {
    "white": _paint_white_noise,
    "pink":  _paint_pink_noise,
    "brown": _paint_brown_noise,
    "rain":  _paint_rain,
    "river": _paint_river,
}

THEMES = {
    "white": {
        "bg_top": (200, 220, 240),
        "bg_bottom": (240, 248, 255),
        "wave_color": (255, 255, 255, 120),
        "text_color": (30, 50, 80),
        "sub_color": (80, 100, 130),
        "accent": (100, 160, 220),
        "emoji": "🌬️",
    },
    "pink": {
        "bg_top": (180, 80, 120),
        "bg_bottom": (255, 160, 180),
        "wave_color": (255, 200, 220, 100),
        "text_color": (255, 255, 255),
        "sub_color": (255, 220, 230),
        "accent": (255, 100, 150),
        "emoji": "🌸",
    },
    "brown": {
        "bg_top": (60, 35, 15),
        "bg_bottom": (140, 90, 50),
        "wave_color": (180, 130, 80, 80),
        "text_color": (255, 240, 210),
        "sub_color": (210, 180, 140),
        "accent": (200, 150, 80),
        "emoji": "🌲",
    },
    "rain": {
        "bg_top": (20, 30, 60),
        "bg_bottom": (60, 80, 120),
        "wave_color": (100, 150, 220, 80),
        "text_color": (200, 230, 255),
        "sub_color": (150, 190, 230),
        "accent": (80, 140, 220),
        "emoji": "🌧️",
    },
    "river": {
        "bg_top": (10, 60, 100),
        "bg_bottom": (30, 140, 160),
        "wave_color": (100, 200, 220, 90),
        "text_color": (220, 250, 255),
        "sub_color": (160, 220, 240),
        "accent": (50, 180, 210),
        "emoji": "🏞️",
    },
}


def _draw_gradient(img: Image.Image, top: tuple, bottom: tuple):
    draw = ImageDraw.Draw(img)
    h = img.height
    for y in range(h):
        r = int(top[0] + (bottom[0] - top[0]) * y / h)
        g = int(top[1] + (bottom[1] - top[1]) * y / h)
        b = int(top[2] + (bottom[2] - top[2]) * y / h)
        draw.line([(0, y), (img.width, y)], fill=(r, g, b))


def _draw_waves(img: Image.Image, color: tuple, count: int = 5, amplitude: int = 28):
    import math
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    for i in range(count):
        y_base = int(h * 0.45 + i * 38)
        points = []
        for x in range(0, w + 1, 4):
            y = y_base + int(amplitude * math.sin((x / w) * 4 * math.pi + i * 0.9))
            points.append((x, y))
        for x in range(w, -1, -4):
            y = y_base + amplitude + 18
            points.append((x, y))
        draw.polygon(points, fill=color)
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


FANTASY_TYPES = {
    "fantasy_library": {"tint": (180, 120,  30), "label1": "WIZARDING LIBRARY", "label2": "Candlelit Study"},
    "medieval_tavern": {"tint": (180,  80,  20), "label1": "MEDIEVAL TAVERN",   "label2": "By the Fire"},
    "enchanted_forest":{"tint": ( 20, 120,  60), "label1": "ENCHANTED FOREST",  "label2": "Mystical Night"},
    "ancient_temple":  {"tint": ( 80,  30, 140), "label1": "ANCIENT TEMPLE",    "label2": "Lost & Silent"},
    "cozy_cottage":    {"tint": ( 90, 140,  30), "label1": "FANTASY COTTAGE",   "label2": "Hobbit-Style"},
    "castle_wind":     {"tint": ( 30,  80, 160), "label1": "CASTLE RAMPARTS",   "label2": "Midnight Wind"},
    "space_station":   {"tint": ( 10,  40, 120), "label1": "DEEP SPACE",        "label2": "Station Ambiance"},
    "dragon_cave":     {"tint": (140,  20,  20), "label1": "DRAGON'S CAVE",     "label2": "Dark & Ancient"},
}


FANTASY_PROMPTS = {
    "fantasy_library":  "Roger Dean progressive rock album cover art style, surreal ancient library with towering bookshelves made of organic stone, glowing candles, floating books and scrolls, waterfalls cascading from floating islands, vivid teal and amber sky, lush alien vegetation, dreamlike and psychedelic, ultra detailed, no text, 16:9",
    "medieval_tavern":  "Roger Dean progressive rock album cover art style, surreal organic tavern built into a giant mushroom, warm golden bioluminescent light, floating lanterns, alien plants, vivid colors, dreamlike fantasy landscape, ultra detailed, no text, 16:9",
    "enchanted_forest": "Roger Dean progressive rock album cover art style, vast surreal enchanted forest with enormous glowing trees, floating islands with cascading waterfalls, vivid emerald and violet sky, alien flora, bioluminescent creatures, ultra detailed, no text, 16:9",
    "ancient_temple":   "Roger Dean progressive rock album cover art style, ancient temple ruins floating on a sky island, dramatic purple and gold sky, organic stone architecture, glowing mystical carvings, mist below, ultra detailed, no text, 16:9",
    "cozy_cottage":     "Roger Dean progressive rock album cover art style, cozy round hobbit cottage nestled on a floating island, warm glowing windows, lush impossible garden, pastel sky with twin moons, organic curved architecture, ultra detailed, no text, 16:9",
    "castle_wind":      "Roger Dean progressive rock album cover art style, dramatic castle perched on floating rock formations, sweeping organic spires, vivid stormy sky with aurora, misty valleys below, epic scale, ultra detailed, no text, 16:9",
    "space_station":    "Roger Dean progressive rock album cover art style, organic bio-mechanical space station floating among vivid nebulae, curved architecture merging with alien crystal formations, deep violet and cyan galaxy, ultra detailed, no text, 16:9",
    "dragon_cave":      "Roger Dean progressive rock album cover art style, vast dragon cave with glowing crystal formations, enormous organic stalactites, volcanic amber light, surreal scale, alien rock textures, vivid red and gold tones, ultra detailed, no text, 16:9",
}


def _fetch_dalle_image(prompt: str) -> Image.Image | None:
    """gpt-image-1でイラストを生成して返す。"""
    try:
        import base64
        from openai import OpenAI
        key = _load_openai_key()
        if not key:
            return None
        client = OpenAI(api_key=key)
        response = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1536x1024",
            quality="low",
            n=1,
        )
        img_data = base64.b64decode(response.data[0].b64_json)
        return Image.open(io.BytesIO(img_data)).convert("RGB")
    except Exception as e:
        print(f"Image generation failed: {e}")
        return None


def _generate_fantasy_thumbnail(sound: dict, output_path: str, photo_seed: int, duration_label: str):
    """ファンタジー専用サムネイル: DALL-E 3イラスト + テキストオーバーレイ."""
    info = FANTASY_TYPES[sound["type"]]
    tint_color = info["tint"]

    # DALL-E 3で生成、失敗時はPixabay写真にフォールバック
    prompt = FANTASY_PROMPTS.get(sound["type"], "")
    photo = _fetch_dalle_image(prompt) if prompt else None
    if photo is None:
        photo = _fetch_photo(sound, seed=photo_seed)
    if photo:
        pw, ph = photo.size
        scale = max(1280 / pw, 720 / ph)
        nw, nh = int(pw * scale), int(ph * scale)
        photo = photo.resize((nw, nh), Image.LANCZOS)
        left = (nw - 1280) // 2
        top  = (nh - 720) // 2
        img = photo.crop((left, top, left + 1280, top + 720))
    else:
        img = Image.new("RGB", (1280, 720), (20, 10, 30))

    img = img.convert("RGBA")

    # 軽いビネットのみ（暗くしすぎない）
    vignette = Image.new("RGBA", img.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(120):
        alpha = int(90 * ((120 - i) / 120) ** 2)
        vd.rectangle([(i, i), (1280 - i, 720 - i)], outline=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, vignette)

    FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
    try:
        font_xl = ImageFont.truetype(f"{FONTS_DIR}/Cinzel-Bold.ttf", 78)
        font_sm = ImageFont.truetype(f"{FONTS_DIR}/Cinzel-Regular.ttf", 26)
    except Exception:
        try:
            font_xl = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 86)
            font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
        except Exception:
            font_xl = font_sm = ImageFont.load_default()

    cx = 1280 // 2

    # 下部グラデーション帯（テキスト部分のみ）
    grad = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for i in range(160):
        alpha = int(200 * (i / 160) ** 2)
        gd.line([(0, 560 + i), (1280, 560 + i)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img, grad)
    draw = ImageDraw.Draw(img)

    # メインタイトル（フォント自動縮小・縁取り付き）
    FONTS_DIR = os.path.join(os.path.dirname(__file__), "fonts")
    t1 = info["label1"]
    font_xl = _fit_font(f"{FONTS_DIR}/Cinzel-Bold.ttf", t1, max_width=1200, max_size=96)
    b1 = draw.textbbox((0, 0), t1, font=font_xl)
    w1 = b1[2] - b1[0]
    _draw_outlined_text(draw, (cx - w1 // 2, 590), t1,
                        font=font_xl, fill=(255, 255, 255), outline=(0, 0, 0), stroke=3)

    # 時間ラベル（左下）
    try:
        font_sm = ImageFont.truetype(f"{FONTS_DIR}/Cinzel-Regular.ttf", 26)
    except Exception:
        font_sm = ImageFont.load_default()
    _draw_outlined_text(draw, (20, 688), duration_label,
                        font=font_sm, fill=(210, 210, 210), outline=(0, 0, 0), stroke=2)

    # SleepScapeブランドバッジ（右下）
    rgb_img = img.convert("RGB")
    _draw_brand_badge(rgb_img)
    rgb_img.save(output_path)


def _fit_font(font_path: str, text: str, max_width: int, max_size: int, min_size: int = 32) -> ImageFont.FreeTypeFont:
    """テキストがmax_width以内に収まるフォントサイズを返す。"""
    size = max_size
    while size >= min_size:
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            return ImageFont.load_default()
        dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        w = dummy.textbbox((0, 0), text, font=font)[2]
        if w <= max_width:
            return font
        size -= 4
    return ImageFont.truetype(font_path, min_size)


def _draw_outlined_text(draw: ImageDraw.ImageDraw, xy: tuple, text: str,
                        font, fill=(255, 255, 255), outline=(0, 0, 0), stroke: int = 3):
    """縁取り付きテキストを描画する。"""
    x, y = xy
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_brand_badge(img: Image.Image):
    """右上にSleepScapeウォーターマークを描画する（背景なし・縁取りテキスト）。"""
    try:
        font_text = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 44)
        font_icon = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 48)
    except Exception:
        font_text = ImageFont.load_default()
        font_icon = font_text

    icon  = "🌙"
    label = "SleepScape"
    margin = 20
    gap = 8

    dummy = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    ib = dummy.textbbox((0, 0), icon,  font=font_icon)
    tb = dummy.textbbox((0, 0), label, font=font_text)
    iw, ih = ib[2] - ib[0], ib[3] - ib[1]
    tw, th = tb[2] - tb[0], tb[3] - tb[1]

    total_w = iw + gap + tw
    # 右上：x = 1280 - total_w - margin, y = margin
    x = 1280 - total_w - margin
    y = margin

    draw = ImageDraw.Draw(img)
    # 🌙アイコン（右上）
    draw.text((x, y + (th - ih) // 2), icon, font=font_icon, embedded_color=True)
    # "SleepScape" テキスト（縁取り付き）
    _draw_outlined_text(draw, (x + iw + gap, y), label,
                        font=font_text, fill=(255, 255, 255), outline=(0, 0, 0), stroke=3)


# 音源タイプ別の絵文字アイコン（サムネイル用）
SOUND_ICONS = {
    "white": "🌬️", "pink": "🌸", "brown": "🌲",
    "rain_light": "🌧️", "rain_heavy": "⛈️", "thunderstorm": "🌩️", "rain_roof": "🏠",
    "ocean": "🌊", "beach": "🏖️", "river": "🏞️", "waterfall": "💧", "forest": "🌲",
    "city": "🌃", "paris": "☕", "cafe": "☕", "library": "📚",
    "fan": "🌀", "airplane": "✈️", "train": "🚂", "fireplace": "🔥",
    "train_underpass": "🚃", "study_hall": "📚", "waiting_room": "🚉",
    "night_drive": "🚗", "electric_fan_real": "🌀",
}


def generate_thumbnail(sound: dict, output_path: str, photo_seed: int = 0, duration_label: str = "1 HOUR"):
    # ファンタジー音源は専用デザインを使用
    if sound["type"] in FANTASY_TYPES:
        return _generate_fantasy_thumbnail(sound, output_path, photo_seed, duration_label)

    # 写真をPixabayから取得、失敗時はイラスト生成にフォールバック
    photo = _fetch_photo(sound, seed=photo_seed)
    if photo:
        pw, ph = photo.size
        scale = max(1280 / pw, 720 / ph)
        nw, nh = int(pw * scale), int(ph * scale)
        photo = photo.resize((nw, nh), Image.LANCZOS)
        left = (nw - 1280) // 2
        top  = (nh - 720) // 2
        img = photo.crop((left, top, left + 1280, top + 720))
    else:
        theme = THEMES.get(sound["type"], THEMES["white"])
        img = Image.new("RGB", (1280, 720))
        painter = LANDSCAPE_PAINTERS.get(sound["type"])
        if painter:
            painter(img)
        else:
            _gradient(img, theme["bg_top"], theme["bg_bottom"])

    # 全体を少し暗くして文字を見やすく
    dimmer = Image.new("RGBA", img.size, (0, 0, 0, 60))
    img = Image.alpha_composite(img.convert("RGBA"), dimmer).convert("RGB")

    # 下部グラデーション帯
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(220):
        alpha = int(210 * (i / 220) ** 1.5)
        od.line([(0, 500 + i), (1280, 500 + i)], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    FONT_PATH = "/System/Library/Fonts/Helvetica.ttc"

    # ① メインタイトル（フォント自動縮小・縁取り付き）
    text1 = sound["label"].upper()
    font_large = _fit_font(FONT_PATH, text1, max_width=1180, max_size=88)
    bbox1 = ImageDraw.Draw(img).textbbox((0, 0), text1, font=font_large)
    w1 = bbox1[2] - bbox1[0]
    draw = ImageDraw.Draw(img)
    _draw_outlined_text(draw, ((1280 - w1) // 2, 555), text1,
                        font=font_large, fill=(255, 255, 255), outline=(0, 0, 0), stroke=3)

    # ② 絵文字アイコン（右寄せ・大きく）
    icon = SOUND_ICONS.get(sound["type"], "🎵")
    try:
        font_icon = ImageFont.truetype("/System/Library/Fonts/Apple Color Emoji.ttc", 72)
        ib = draw.textbbox((0, 0), icon, font=font_icon)
        draw.text((1280 - (ib[2] - ib[0]) - 24, 530), icon, font=font_icon, embedded_color=True)
    except Exception:
        pass  # 絵文字フォントが無ければスキップ

    # ③ サブテキスト（縁取り付き）
    try:
        font_small = ImageFont.truetype(FONT_PATH, 32)
    except Exception:
        font_small = ImageFont.load_default()
    text2 = f"{duration_label}  ·  Sleep  ·  Focus  ·  Relax"
    bbox2 = draw.textbbox((0, 0), text2, font=font_small)
    w2 = bbox2[2] - bbox2[0]
    _draw_outlined_text(draw, ((1280 - w2) // 2, 655), text2,
                        font=font_small, fill=(210, 225, 240), outline=(0, 0, 0), stroke=2)

    # ④ SleepScapeブランドバッジ（右下）
    _draw_brand_badge(img)

    img.save(output_path)


TITLE_TEMPLATES = {
    "white":      "{d} of Pure White Noise 🤍 | Fall Asleep Fast | Baby Sleep & Deep Focus",
    "pink":       "Pink Noise {d} 🌸 | The Best Sound for Deep Sleep & Study",
    "brown":      "Brown Noise {d} 🌿 | Calm Your Mind | ADHD Focus & Deep Sleep",
    "rain_light": "Gentle Rain on Window {d} 🌧 | Cozy Sleep Sounds | Study & Relax",
    "rain_heavy": "Heavy Rain & Stormy Night {d} ⛈ | Sleep Instantly | Stress Relief",
    "thunderstorm":"Thunder & Rain {d} 🌩 | Powerful Sleep Sounds | Anxiety Relief",
    "rain_roof":  "Rain on Rooftop {d} 🏠 | Cozy Rainy Night | Sleep & Focus",
    "ocean":      "Ocean Waves {d} 🌊 | Relaxing Beach Sounds | Deep Sleep & Meditation",
    "beach":      "Tropical Beach Sounds {d} 🏖 | Paradise Sleep Sounds | Stress Relief",
    "river":      "Mountain River Stream {d} 🏞 | Peaceful Nature Sounds | Sleep & Focus",
    "waterfall":  "Waterfall Sounds {d} 💧 | Pure Nature White Noise | Deep Sleep",
    "forest":     "Forest Sounds at Night {d} 🌲 | Nature ASMR | Sleep & Meditation",
    "city":       "City Ambiance {d} 🌃 | Urban White Noise | Focus & Productivity",
    "paris":      "Paris Street Café Ambiance {d} ☕🗼 | Study in France | Focus Music",
    "cafe":       "Coffee Shop Ambiance {d} ☕ | Study & Work Music | Café Sounds",
    "library":    "Quiet Library Ambiance {d} 📚 | Focus & Study Music | Deep Concentration",
    "fan":        "Electric Fan White Noise {d} 🌀 | Block Outside Noise | Baby Sleep",
    "airplane":   "Airplane Cabin Noise {d} ✈️ | White Noise for Sleep | Long Flight Sounds",
    "train":      "Train Journey Sounds {d} 🚂 | Relaxing Rail Ambiance | Sleep & Focus",
    "fireplace":       "Crackling Fireplace {d} 🔥 | Cozy Winter Sounds | Sleep & Relax",
    # ── ファンタジー・世界観系 ──
    "fantasy_library": "Ancient Magic Library Ambiance 📚🕯️ | {d} D&D Study & Focus Music",
    "medieval_tavern": "Medieval Tavern Ambiance 🍺🔥 | {d} D&D Fantasy RPG Music",
    "enchanted_forest":"Enchanted Forest Ambiance 🌿✨ | {d} D&D Fantasy RPG Music",
    "ancient_temple":  "Ancient Temple Ambiance 🏛️🌙 | {d} Dark Fantasy D&D Music",
    "cozy_cottage":    "Cozy Cottage Ambiance 🏡📖 | {d} Fantasy RPG Relaxing Music",
    "castle_wind":     "Castle Ramparts Ambiance 🏰🌬️ | {d} Medieval D&D Fantasy Music",
    "space_station":   "Deep Space Station Ambiance 🚀🌌 | {d} Sci-Fi RPG Focus Music",
    "dragon_cave":     "Dragon's Cave Ambiance 🐉🔥 | {d} Dark Fantasy D&D Music",
    # ── 実録音源 ──
    "train_underpass": "Train Underpass Ambiance {d} 🚃 | Urban White Noise | Focus & Sleep",
    "study_hall":      "Study Hall Ambiance {d} 📚 | Quiet Background Noise | Focus & Deep Work",
    "waiting_room":    "Station Waiting Room Ambiance {d} 🚉 | Background Noise | Study & Focus",
    "night_drive":     "Night Drive Ambiance {d} 🚗 | Relaxing Car Sounds | Sleep & Focus",
    "electric_fan_real": "Electric Fan White Noise {d} 🌀 | Real Fan Sound | Deep Sleep & Focus",
}

# アフィリエイトリンク（カテゴリ別）
AFFILIATE_LINKS = {
    "default": """\
🛒 Recommended for better sleep:
🔊 White Noise Machine → https://amzn.to/3R3qsMx
🎧 Sleep Headphones (Bluetooth) → https://amzn.to/4fjALG3
😴 Blackout Sleep Mask → https://amzn.to/42CF7Rg
🔈 Pillow Speaker → https://amzn.to/4doJIvg""",

    "fireplace": """\
🛒 Create the perfect cozy atmosphere:
🔥 Fireplace Crackling Video → https://amzn.to/4npvJd8
🎧 Sleep Headphones (Bluetooth) → https://amzn.to/4fjALG3
😴 Blackout Sleep Mask → https://amzn.to/42CF7Rg
🔈 Pillow Speaker → https://amzn.to/4doJIvg""",

    "rain": """\
🛒 Enhance your rainy night experience:
🌧️ Rain Sound Machine → https://amzn.to/3QYw0bb
🎧 Sleep Headphones (Bluetooth) → https://amzn.to/4fjALG3
😴 Blackout Sleep Mask → https://amzn.to/42CF7Rg
🔈 Pillow Speaker → https://amzn.to/4doJIvg""",

    "nature": """\
🛒 Bring nature sounds into your space:
🔊 White Noise Machine → https://amzn.to/3R3qsMx
🔉 Waterproof Bluetooth Speaker → https://amzn.to/4tvbZWX
🎧 Sleep Headphones (Bluetooth) → https://amzn.to/4fjALG3
😴 Blackout Sleep Mask → https://amzn.to/42CF7Rg""",

    "fantasy": """\
🛒 Level up your tabletop RPG session:
🐉 D&D Monster Manual → https://amzn.to/4nyf7Ak
🎧 Gaming Headset → https://amzn.to/4fjALG3
🔈 Bluetooth Speaker → https://amzn.to/4tvbZWX""",

    "study": """\
🛒 Upgrade your study setup:
🎧 Noise-Canceling Headphones → https://amzn.to/4wvOyQh
💡 LED Desk Lamp (USB) → https://amzn.to/4wAAgxM
🕶️ Blue Light Blocking Glasses → https://amzn.to/4dzFSQb
🔊 White Noise Machine → https://amzn.to/3R3qsMx""",

    "travel": """\
🛒 Make every journey more comfortable:
🛏️ Travel Neck Pillow → https://amzn.to/43doCLH
🎧 Wireless Earbuds (Noise-Canceling) → https://amzn.to/4ufS1AG
😴 Travel Eye Mask → https://amzn.to/42CF7Rg
🔋 Portable Charger → https://amzn.to/XXXXXXX""",

    "fan": """\
🛒 Create the perfect sleep environment:
🌀 Tower Fan / Circulator → https://amzn.to/4fb6Sbh
🌬️ Air Purifier → https://amzn.to/492onGS
🔊 White Noise Machine → https://amzn.to/3R3qsMx
😴 Blackout Sleep Mask → https://amzn.to/42CF7Rg""",
}

# 音源タイプ → アフィリエイトカテゴリのマッピング
AFFILIATE_CATEGORY = {
    # 雨・嵐系
    "rain_light":   "rain",
    "rain_heavy":   "rain",
    "thunderstorm": "rain",
    "rain_roof":    "rain",
    # 自然系
    "ocean":        "nature",
    "beach":        "nature",
    "river":        "nature",
    "waterfall":    "nature",
    "forest":       "nature",
    # 暖炉
    "fireplace":    "fireplace",
    # ファンタジー系
    "fantasy_library":  "fantasy",
    "medieval_tavern":  "fantasy",
    "enchanted_forest": "fantasy",
    "ancient_temple":   "fantasy",
    "cozy_cottage":     "fantasy",
    "castle_wind":      "fantasy",
    "space_station":    "fantasy",
    "dragon_cave":      "fantasy",
    # 集中・学習系
    "library":      "study",
    "cafe":         "study",
    "paris":        "study",
    "study_hall":   "study",
    # 移動・旅行系
    "airplane":         "travel",
    "train":            "travel",
    "night_drive":      "travel",
    "train_underpass":  "travel",
    "waiting_room":     "travel",
    # ファン・空調系
    "fan":              "fan",
    "electric_fan_real":"fan",
    # 純粋な睡眠ノイズ → default (white, pink, brown, city)
}

DESCRIPTION_TEMPLATES = {
    "default": """{headline}

😴 Can't sleep? Put this on and drift off in minutes.
📖 Studying or working? Block distractions and enter deep focus.
👶 Great for babies and toddlers who need consistent sleep sounds.
🧘 Perfect background for meditation and mindfulness.

▶ How to use:
→ Set volume to a comfortable level (30–50% recommended)
→ Use a Bluetooth speaker or headphones for best results
→ Enable "Loop" to play all night

🔔 Subscribe for new sleep sounds uploaded every day.

{affiliate}

*As an Amazon Associate I earn from qualifying purchases.

{tags}""",
}


def build_metadata(sound: dict, hours: int = 1) -> dict:
    duration_str = f"{hours} Hour" if hours == 1 else f"{hours} Hours"
    tmpl = TITLE_TEMPLATES.get(sound["type"],
           "{d} of {label} | Sleep, Focus & Relaxation")
    title = tmpl.format(d=duration_str, label=sound["label"])

    headline = f"{duration_str} of uninterrupted {sound['label'].lower()} — one of the most effective sounds for deep sleep, focus, and relaxation."
    hashtags = " ".join([
        f"#{sound['label'].lower().replace(' ', '')}",
        "#sleepsounds", "#whitenoise", "#deepsleep",
        "#studymusic", "#ambientnoise", "#asmr",
        f"#{duration_str.lower().replace(' ', '')}",
    ])
    affiliate_key = AFFILIATE_CATEGORY.get(sound["type"], "default")
    affiliate = AFFILIATE_LINKS[affiliate_key]
    description = DESCRIPTION_TEMPLATES["default"].format(
        headline=headline, affiliate=affiliate, tags=hashtags
    )

    fantasy_types = {"fantasy_library", "medieval_tavern", "enchanted_forest",
                     "ancient_temple", "cozy_cottage", "castle_wind",
                     "space_station", "dragon_cave"}
    if sound["type"] in fantasy_types:
        tags = [
            sound["label"], "fantasy ambiance", "D&D music", "DnD ambiance",
            "tabletop RPG music", "RPG music", "fantasy sounds", "ambient music",
            "study music", "relaxing fantasy music", "fantasy roleplay",
            "TTRPG music", "lofi fantasy", "magical ambiance", duration_str,
        ]
    else:
        tags = [
            sound["label"], "sleep sounds", "white noise", "deep sleep",
            "study music", "ambient noise", "ASMR", "relaxation", "focus",
            "baby sleep", duration_str, sound["subtitle"],
        ]
    return {"title": title, "description": description, "tags": tags}
