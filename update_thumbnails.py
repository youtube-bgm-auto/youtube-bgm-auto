import os
import tempfile
import logging
import sys
from upload import get_authenticated_service
from generate import SOUNDS, generate_thumbnail
from googleapiclient.http import MediaFileUpload

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# タイトルキーワード → SOUNDSのtypeにマッピング
KEYWORD_MAP = [
    ("paris",       "paris"),
    ("coffee shop", "cafe"),
    ("cafe",        "cafe"),
    ("library",     "library"),
    ("city",        "city"),
    ("urban",       "city"),
    ("airplane",    "airplane"),
    ("train",       "train"),
    ("fireplace",   "fireplace"),
    ("fire",        "fireplace"),
    ("fan",         "fan"),
    ("beach",       "beach"),
    ("ocean",       "ocean"),
    ("wave",        "ocean"),
    ("waterfall",   "waterfall"),
    ("river",       "river"),
    ("stream",      "river"),
    ("forest",      "forest"),
    ("thunder",     "thunderstorm"),
    ("storm",       "thunderstorm"),
    ("heavy rain",  "rain_heavy"),
    ("rain on roof","rain_roof"),
    ("rain",        "rain_light"),
    ("brown noise", "brown"),
    ("pink noise",  "pink"),
    ("white noise", "white"),
    ("colorado",    "river"),
]

SOUNDS_BY_TYPE = {s["type"]: s for s in SOUNDS}


def detect_sound_type(title: str) -> str:
    title_lower = title.lower()
    for keyword, sound_type in KEYWORD_MAP:
        if keyword in title_lower:
            return sound_type
    return "white"


def get_my_videos(youtube, max_results=50):
    # チャンネルID取得
    ch = youtube.channels().list(part="id", mine=True).execute()
    channel_id = ch["items"][0]["id"]

    # アップロード済みプレイリストID取得
    ch_detail = youtube.channels().list(
        part="contentDetails", id=channel_id
    ).execute()
    uploads_id = ch_detail["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    # 動画一覧取得
    videos = []
    next_page = None
    while True:
        params = dict(part="snippet", playlistId=uploads_id, maxResults=50)
        if next_page:
            params["pageToken"] = next_page
        res = youtube.playlistItems().list(**params).execute()
        for item in res["items"]:
            videos.append({
                "video_id": item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
            })
        next_page = res.get("nextPageToken")
        if not next_page or len(videos) >= max_results:
            break
    return videos


def update_thumbnail(youtube, video_id: str, thumb_path: str):
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumb_path),
    ).execute()


def main():
    youtube = get_authenticated_service()
    videos = get_my_videos(youtube)
    logging.info(f"Found {len(videos)} videos")

    for v in videos:
        title = v["title"]
        video_id = v["video_id"]
        sound_type = detect_sound_type(title)
        sound = SOUNDS_BY_TYPE.get(sound_type, SOUNDS_BY_TYPE["white"])

        logging.info(f'"{title}"')
        logging.info(f"  → type: {sound_type} | sound: {sound['label']}")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            thumb_path = f.name

        try:
            generate_thumbnail(sound, thumb_path, photo_seed=hash(video_id) % 20)
            update_thumbnail(youtube, video_id, thumb_path)
            logging.info(f"  ✓ Thumbnail updated: https://www.youtube.com/watch?v={video_id}")
        except Exception as e:
            logging.error(f"  ✗ Failed: {e}")
        finally:
            if os.path.exists(thumb_path):
                os.remove(thumb_path)

    logging.info("All done.")


if __name__ == "__main__":
    main()
