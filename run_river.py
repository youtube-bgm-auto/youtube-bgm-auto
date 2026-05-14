import os
import sys
import logging
from datetime import datetime
from generate import generate_video, generate_thumbnail, build_metadata
from upload import upload_video

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

RIVER_SOUND = {
    "type": "river",
    "label": "River Stream Sounds",
    "subtitle": "Colorado River Stream",
    "ffmpeg_src": "anoisesrc=color=pink[n];[n]afftfilt=real='hypot(re,im)*sin(random(0)*2*3.14)':imag='hypot(re,im)*cos(random(1)*2*3.14)':win_size=512:overlap=0.75",
}

RIVER_METADATA = {
    "title": "Colorado River Stream Sounds | 1 Hour | Baby Sleep, Study & Relaxation",
    "description": """Calming sounds of the Colorado River — one of America's most iconic rivers flowing through the Grand Canyon.

This 1-hour river stream recording helps you:
✔ Fall asleep faster and stay asleep longer
✔ Soothe babies and young children at bedtime
✔ Focus while studying or working
✔ Relax and reduce stress

📌 Tips for use:
- Play at a low to moderate volume
- Perfect for naptime, bedtime, meditation, or background work noise
- Works great with sleep masks and white noise machines

🌊 Famous American rivers featured in our channel:
Colorado River · Mississippi River · Yellowstone River · Hudson River

🔔 Subscribe for daily sleep sounds, nature sounds, and white noise.

#riversounds #sleepsounds #coloradoriver #babysleep #naturalsounds #relax #studymusic #whitenoise #americanrivers""",
    "tags": [
        "river sounds", "stream sounds", "colorado river", "baby sleep",
        "sleep sounds", "nature sounds", "relaxation", "study music",
        "white noise", "1 hour", "american rivers", "focus",
    ],
}


def main():
    os.makedirs(TMP_DIR, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    video_path = os.path.join(TMP_DIR, f"video_{stamp}.mp4")
    thumb_path = os.path.join(TMP_DIR, f"thumb_{stamp}.png")

    logging.info("Generating river sound video...")
    generate_video(RIVER_SOUND, video_path)

    logging.info("Generating thumbnail...")
    generate_thumbnail(RIVER_SOUND, thumb_path)

    logging.info(f"Title: {RIVER_METADATA['title']}")
    video_id = upload_video(video_path, thumb_path, RIVER_METADATA)
    logging.info(f"Done: https://www.youtube.com/watch?v={video_id}")

    os.remove(video_path)
    os.remove(thumb_path)


if __name__ == "__main__":
    main()
