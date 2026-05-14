"""
コメント自動返信:
- 全動画の未返信コメントを取得
- 内容に応じたテンプレートで返信
- 返信済みIDをJSONに記録して重複防止
"""
import os
import json
import logging
import re
from upload import get_authenticated_service

REPLIED_FILE = os.path.join(os.path.dirname(__file__), "replied_comments.json")

# 返信テンプレート（コメント内容でパターン分類）
TEMPLATES = {
    "request": (
        "Thank you for the suggestion! 🙏 "
        "We'll do our best to add more sounds like that. "
        "Stay tuned and subscribe so you don't miss it! 🎵"
    ),
    "positive": (
        "Thank you so much for the kind words! 😊 "
        "Really glad it's helping. "
        "New sounds uploaded every day — hope to see you again! 💙"
    ),
    "baby": (
        "So happy to hear that! 👶✨ "
        "Hope your little one keeps sleeping soundly. "
        "We upload new sleep sounds every day! 🤍"
    ),
    "study": (
        "That's awesome — keep up the great work! 📚☕ "
        "Glad the sounds are helping you focus. "
        "New ambient sounds added daily! 🎵"
    ),
    "default": (
        "Thank you for watching and leaving a comment! 😊 "
        "We upload new sleep & ambient sounds every day. "
        "Hope to see you again! 💙"
    ),
}

# キーワードでパターンを判定
PATTERNS = [
    ("request",  r"request|suggest|can you (make|do|add)|more .*(sound|hour|video)|please (make|add)"),
    ("baby",     r"baby|infant|toddler|newborn|kid|child|daughter|son|sleep(ing)? (through|all)"),
    ("study",    r"study|focus|work|concentrat|productiv|exam|homework|essay"),
    ("positive", r"love|amazing|great|perfect|thank|awesome|wonderful|best|helpful|relax|calm|sleep"),
]


def _classify(text: str) -> str:
    t = text.lower()
    for key, pattern in PATTERNS:
        if re.search(pattern, t):
            return key
    return "default"


def _load_replied() -> set:
    if os.path.exists(REPLIED_FILE):
        with open(REPLIED_FILE) as f:
            return set(json.load(f))
    return set()


def _save_replied(ids: set):
    with open(REPLIED_FILE, "w") as f:
        json.dump(sorted(ids), f, indent=2)


def run_auto_reply(dry_run: bool = False):
    youtube = get_authenticated_service()
    replied = _load_replied()
    new_replies = 0

    # 全動画IDを取得
    ch = youtube.channels().list(part="contentDetails", mine=True).execute()
    uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids = []
    next_page = None
    while True:
        params = dict(part="snippet", playlistId=uploads_id, maxResults=50)
        if next_page:
            params["pageToken"] = next_page
        res = youtube.playlistItems().list(**params).execute()
        for item in res["items"]:
            video_ids.append(item["snippet"]["resourceId"]["videoId"])
        next_page = res.get("nextPageToken")
        if not next_page:
            break

    # 各動画のコメントを処理
    for video_id in video_ids:
        try:
            res = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=100,
                order="time",
            ).execute()
        except Exception as e:
            logging.warning(f"Failed to fetch comments for {video_id}: {e}")
            continue

        for thread in res.get("items", []):
            top = thread["snippet"]["topLevelComment"]
            comment_id = top["id"]
            text = top["snippet"]["textDisplay"]
            author = top["snippet"]["authorDisplayName"]
            reply_count = thread["snippet"]["totalReplyCount"]

            # 返信済みまたはすでに返信があればスキップ
            if comment_id in replied or reply_count > 0:
                continue

            category = _classify(text)
            reply_text = TEMPLATES[category]

            logging.info(f"[{category}] @{author}: {text[:60]}")
            logging.info(f"  → {reply_text[:60]}...")

            if not dry_run:
                try:
                    youtube.comments().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "parentId": comment_id,
                                "textOriginal": reply_text,
                            }
                        },
                    ).execute()
                    replied.add(comment_id)
                    new_replies += 1
                except Exception as e:
                    logging.warning(f"Failed to reply to {comment_id}: {e}")

    _save_replied(replied)
    print(f"✅ 返信完了: {new_replies} 件")
    return new_replies


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    dry = "--dry-run" in sys.argv
    if dry:
        print("=== DRY RUN（実際には返信しません）===")
    run_auto_reply(dry_run=dry)
