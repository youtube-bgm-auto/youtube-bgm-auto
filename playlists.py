"""
プレイリスト管理:
- カテゴリ別プレイリストを自動作成
- 動画を適切なプレイリストに振り分け
- 新規投稿時に自動追加
"""
import os
import json
import logging

PLAYLIST_FILE = os.path.join(os.path.dirname(__file__), "playlists.json")

# カテゴリ定義: sound type → playlist key
SOUND_TO_PLAYLIST = {
    "white":       "baby_sleep",
    "pink":        "baby_sleep",
    "fan":         "baby_sleep",
    "brown":       "focus",
    "library":     "focus",
    "city":        "focus",
    "paris":       "focus",
    "cafe":        "focus",
    "airplane":    "focus",
    "train":       "focus",
    "rain_light":  "nature",
    "rain_heavy":  "nature",
    "thunderstorm":"nature",
    "rain_roof":   "nature",
    "ocean":       "nature",
    "beach":       "nature",
    "river":       "nature",
    "waterfall":   "nature",
    "forest":      "nature",
    "fireplace":       "cozy",
    # ファンタジー・世界観系
    "fantasy_library": "fantasy",
    "medieval_tavern": "fantasy",
    "enchanted_forest":"fantasy",
    "ancient_temple":  "fantasy",
    "cozy_cottage":    "fantasy",
    "castle_wind":     "fantasy",
    "space_station":   "fantasy",
    "dragon_cave":     "fantasy",
}

PLAYLIST_DEFS = {
    "baby_sleep": {
        "title": "Baby Sleep Sounds 👶 | White Noise & Gentle Sounds",
        "description": "The best white noise and gentle sounds to help babies and toddlers fall asleep fast. New videos added every day.",
    },
    "focus": {
        "title": "Study & Focus Music ☕ | Ambient Sounds for Productivity",
        "description": "Ambient sounds for deep focus, studying, and remote work. Coffee shop sounds, city ambiance, and more.",
    },
    "nature": {
        "title": "Nature Sleep Sounds 🌊 | Rain, Ocean, River & Forest",
        "description": "Relaxing nature sounds for deep sleep and meditation. Rain, ocean waves, river streams, and forest ambiance.",
    },
    "cozy": {
        "title": "Cozy Sleep Sounds 🔥 | Fireplace, Rain & Warm Ambiance",
        "description": "Warm and cozy ambient sounds to help you relax and sleep. Crackling fireplace, rain on rooftop, and more.",
    },
    "fantasy": {
        "title": "Fantasy & Sci-Fi Worlds 🏰 | Immersive Ambient Sounds",
        "description": "Immersive ambient soundscapes inspired by fantasy and sci-fi worlds. Wizarding libraries, medieval taverns, enchanted forests, and more.",
    },
}


def _load_playlist_ids() -> dict:
    if os.path.exists(PLAYLIST_FILE):
        with open(PLAYLIST_FILE) as f:
            return json.load(f)
    return {}


def _save_playlist_ids(ids: dict):
    with open(PLAYLIST_FILE, "w") as f:
        json.dump(ids, f, indent=2)


def ensure_playlists(youtube) -> dict:
    """プレイリストが存在しなければ作成してIDを返す。"""
    ids = _load_playlist_ids()
    for key, defn in PLAYLIST_DEFS.items():
        if key in ids:
            continue
        res = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": defn["title"],
                    "description": defn["description"],
                },
                "status": {"privacyStatus": "public"},
            }
        ).execute()
        ids[key] = res["id"]
        logging.info(f"Created playlist: {defn['title']} ({res['id']})")
    _save_playlist_ids(ids)
    return ids


def add_to_playlist(youtube, video_id: str, sound_type: str):
    """動画をカテゴリに合ったプレイリストに追加する。"""
    playlist_key = SOUND_TO_PLAYLIST.get(sound_type)
    if not playlist_key:
        return
    ids = _load_playlist_ids()
    playlist_id = ids.get(playlist_key)
    if not playlist_id:
        logging.warning(f"Playlist not found for key: {playlist_key}")
        return
    youtube.playlistItems().insert(
        part="snippet",
        body={
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {
                    "kind": "youtube#video",
                    "videoId": video_id,
                },
            }
        }
    ).execute()
    logging.info(f"Added {video_id} to playlist: {playlist_key}")


def sync_existing_videos(youtube):
    """既存の全動画を適切なプレイリストに振り分ける。"""
    from generate import SOUNDS
    from update_thumbnails import detect_sound_type

    ensure_playlists(youtube)

    ch = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    res = youtube.playlistItems().list(
        part="snippet", playlistId=uploads_id, maxResults=50
    ).execute()

    for item in res["items"]:
        video_id = item["snippet"]["resourceId"]["videoId"]
        title    = item["snippet"]["title"]
        stype    = detect_sound_type(title)
        try:
            add_to_playlist(youtube, video_id, stype)
            logging.info(f"  ✓ {title[:50]}")
        except Exception as e:
            logging.warning(f"  ✗ {title[:50]}: {e}")
