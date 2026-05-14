import os
import sys
import logging
from datetime import datetime
from generate import pick_sound, generate_video, generate_thumbnail, build_metadata, save_photo_to_file, fetch_background_video
from upload import upload_video, get_authenticated_service
from playlists import ensure_playlists, add_to_playlist

LOG_FILE = os.path.join(os.path.dirname(__file__), "run.log")
TMP_DIR = os.path.join(os.path.dirname(__file__), "tmp")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)


def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    sound = pick_sound()
    logging.info(f"Selected sound: {sound['label']}")

    # プレイリスト準備（未作成なら自動作成）
    youtube = get_authenticated_service()
    ensure_playlists(youtube)

    video_1h = os.path.join(TMP_DIR, f"video_{stamp}_1h.mp4")
    video_8h = os.path.join(TMP_DIR, f"video_{stamp}_8h.mp4")
    thumb_1h = os.path.join(TMP_DIR, f"thumb_{stamp}_1h.png")
    thumb_8h = os.path.join(TMP_DIR, f"thumb_{stamp}_8h.png")
    photo    = os.path.join(TMP_DIR, f"photo_{stamp}.jpg")

    try:
        # ── 背景素材をダウンロード（動画優先、失敗時は写真）──
        logging.info("Downloading background video...")
        bg_video = os.path.join(TMP_DIR, f"bg_{stamp}.mp4")
        if fetch_background_video(sound, bg_video, seed=0):
            photo = bg_video
            logging.info("Background video ready.")
        else:
            logging.info("Video unavailable, falling back to photo...")
            if not save_photo_to_file(sound, photo, seed=0):
                photo = None
                logging.warning("Photo download also failed, using black screen.")

        # ── 1時間版を生成（写真背景＋波形）──
        logging.info("[1h] Generating video...")
        generate_video(sound, video_1h, duration=3600, photo_path=photo)

        # ── 8時間版は1時間版をループコピー（数秒で完了）──
        logging.info("[8h] Generating video (loop copy)...")
        generate_video(sound, video_8h, duration=28800, base_path=video_1h)

        # ── サムネイル生成（別写真を使用）──
        logging.info("Generating thumbnails...")
        generate_thumbnail(sound, thumb_1h, photo_seed=0, duration_label="1 HOUR")
        generate_thumbnail(sound, thumb_8h, photo_seed=1, duration_label="8 HOURS")

        # ── 1時間版アップロード ──
        meta_1h = build_metadata(sound, hours=1)
        logging.info(f"[1h] Uploading: {meta_1h['title']}")
        vid_1h = upload_video(video_1h, thumb_1h, meta_1h)
        logging.info(f"[1h] Done: https://www.youtube.com/watch?v={vid_1h}")
        add_to_playlist(youtube, vid_1h, sound["type"])

        # ── 8時間版アップロード ──
        meta_8h = build_metadata(sound, hours=8)
        logging.info(f"[8h] Uploading: {meta_8h['title']}")
        vid_8h = upload_video(video_8h, thumb_8h, meta_8h)
        logging.info(f"[8h] Done: https://www.youtube.com/watch?v={vid_8h}")
        add_to_playlist(youtube, vid_8h, sound["type"])

        logging.info("All versions uploaded successfully.")

    finally:
        for path in [video_1h, video_8h, thumb_1h, thumb_8h, photo, bg_video]:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    main()
