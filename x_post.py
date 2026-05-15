"""
X (Twitter) への自動投稿モジュール
YouTube動画アップロード後に呼び出す
"""
import os
import tweepy
from dotenv import load_dotenv

load_dotenv()

def get_x_client():
    return tweepy.Client(
        consumer_key=os.getenv("X_API_KEY"),
        consumer_secret=os.getenv("X_API_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )

def post_video_tweet(title: str, video_id: str, hours: int) -> str | None:
    """
    新規動画をXに告知ツイート
    例: New upload 🎵 Ocean Waves 1 Hour 🌊 | ...
        youtu.be/XXXXXXXXX
        #AmbientMusic #SleepMusic #WhiteNoise
    """
    url = f"https://youtu.be/{video_id}"

    # 時間表記
    duration = "1 Hour" if hours == 1 else "8 Hours"

    tweet = (
        f"New upload 🎵\n"
        f"{title}\n"
        f"\n"
        f"{url}\n"
        f"\n"
        f"#AmbientMusic #SleepMusic #RelaxingMusic #StudyMusic #Meditation"
    )

    try:
        client = get_x_client()
        response = client.create_tweet(text=tweet)
        tweet_id = response.data["id"]
        print(f"[X] Posted: https://x.com/SleepScapeDaily/status/{tweet_id}")
        return tweet_id
    except Exception as e:
        print(f"[X] Failed to post: {e}")
        return None


def post_shorts_tweet(title: str, video_id: str) -> str | None:
    """Shorts動画をXに告知ツイート"""
    url = f"https://youtu.be/{video_id}"

    tweet = (
        f"New Short 🎵\n"
        f"{title}\n"
        f"\n"
        f"{url}\n"
        f"\n"
        f"#Shorts #AmbientMusic #SleepMusic #RelaxingMusic"
    )

    try:
        client = get_x_client()
        response = client.create_tweet(text=tweet)
        tweet_id = response.data["id"]
        print(f"[X] Posted Short: https://x.com/SleepScapeDaily/status/{tweet_id}")
        return tweet_id
    except Exception as e:
        print(f"[X] Failed to post Short: {e}")
        return None


if __name__ == "__main__":
    # テスト投稿
    post_video_tweet(
        title="Ocean Waves 1 Hour 🌊 | Relaxing Beach Sounds | Deep Sleep & Meditation",
        video_id="TEST_ID",
        hours=1,
    )
