"""
ファンタジー動画キュー投稿スクリプト:
- FANTASY_QUEUE に定義した順に1日1本ずつ投稿
- fantasy_queue.json で進捗を管理
- キューが空になったら何もしない
"""
import os
import sys
import json
import logging
from datetime import datetime
from generate import generate_video, generate_thumbnail, build_metadata, save_photo_to_file, fetch_background_video, SOUNDS
from upload import upload_video, get_authenticated_service
from playlists import ensure_playlists, add_to_playlist

LOG_FILE  = os.path.join(os.path.dirname(__file__), "run.log")
TMP_DIR   = os.path.join(os.path.dirname(__file__), "tmp")
STATE_FILE = os.path.join(os.path.dirname(__file__), "fantasy_queue.json")

# 投稿する順番
FANTASY_QUEUE = [
    "enchanted_forest",
    "ancient_temple",
    "cozy_cottage",
    "castle_wind",
    "space_station",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"done": []}


def _save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    state = _load_state()
    done = state.get("done", [])

    # 未投稿の次の1本を選ぶ
    remaining = [t for t in FANTASY_QUEUE if t not in done]
    if not remaining:
        logging.info("Fantasy queue is empty. Nothing to upload.")
        return

    sound_type = remaining[0]
    sound = next((s for s in SOUNDS if s["type"] == sound_type), None)
    if sound is None:
        logging.error(f"Sound not found: {sound_type}")
        return

    logging.info(f"Fantasy upload: {sound['label']}")
    os.makedirs(TMP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    video_1h = os.path.join(TMP_DIR, f"video_{stamp}_1h.mp4")
    video_8h = os.path.join(TMP_DIR, f"video_{stamp}_8h.mp4")
    thumb_1h = os.path.join(TMP_DIR, f"thumb_{stamp}_1h.png")
    thumb_8h = os.path.join(TMP_DIR, f"thumb_{stamp}_8h.png")
    bg_video  = os.path.join(TMP_DIR, f"bg_{stamp}.mp4")
    photo     = os.path.join(TMP_DIR, f"photo_{stamp}.jpg")

    try:
        youtube = get_authenticated_service()
        ensure_playlists(youtube)

        logging.info("Downloading background video...")
        if fetch_background_video(sound, bg_video, seed=0):
            photo = bg_video
        else:
            if not save_photo_to_file(sound, photo, seed=0):
                photo = None

        logging.info("[1h] Generating video...")
        generate_video(sound, video_1h, duration=3600, photo_path=photo)
        logging.info("[8h] Generating video...")
        generate_video(sound, video_8h, duration=28800, base_path=video_1h)

        logging.info("Generating thumbnails...")
        generate_thumbnail(sound, thumb_1h, photo_seed=0, duration_label="1 HOUR")
        generate_thumbnail(sound, thumb_8h, photo_seed=1, duration_label="8 HOURS")

        meta_1h = build_metadata(sound, hours=1)
        logging.info(f"[1h] Uploading: {meta_1h['title']}")
        vid_1h = upload_video(video_1h, thumb_1h, meta_1h)
        logging.info(f"[1h] Done: https://www.youtube.com/watch?v={vid_1h}")
        add_to_playlist(youtube, vid_1h, sound["type"])

        meta_8h = build_metadata(sound, hours=8)
        logging.info(f"[8h] Uploading: {meta_8h['title']}")
        vid_8h = upload_video(video_8h, thumb_8h, meta_8h)
        logging.info(f"[8h] Done: https://www.youtube.com/watch?v={vid_8h}")
        add_to_playlist(youtube, vid_8h, sound["type"])

        # 投稿済みに記録
        done.append(sound_type)
        _save_state({"done": done})
        logging.info(f"Fantasy queue: {len(done)}/{len(FANTASY_QUEUE)} done.")

    finally:
        for path in [video_1h, video_8h, thumb_1h, thumb_8h, bg_video]:
            if path and os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    main()
