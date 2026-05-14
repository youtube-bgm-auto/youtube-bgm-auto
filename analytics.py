"""
週次アナリティクスレポート:
- 総再生数・視聴時間・登録者数を取得
- 収益化条件の達成率を表示
- 上位動画ランキング
"""
import os
import json
import logging
from datetime import datetime, timedelta
from upload import get_authenticated_service

REPORT_FILE = os.path.join(os.path.dirname(__file__), "analytics_log.json")

# 収益化条件
MONETIZE_SUBS     = 1000
MONETIZE_HOURS    = 4000


def _load_log() -> list:
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE) as f:
            return json.load(f)
    return []


def _save_log(log: list):
    with open(REPORT_FILE, "w") as f:
        json.dump(log[-52:], f, indent=2, ensure_ascii=False)  # 1年分保持


def fetch_report():
    youtube = get_authenticated_service()

    # チャンネル基本情報（登録者・総再生数）
    ch = youtube.channels().list(
        part="statistics", mine=True
    ).execute()
    stats = ch["items"][0]["statistics"]
    subs        = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    video_count = int(stats.get("videoCount", 0))

    # 全動画の個別再生数を取得
    uploads_id = youtube.channels().list(
        part="contentDetails", mine=True
    ).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    videos = []
    next_page = None
    while True:
        params = dict(part="snippet,contentDetails",
                      playlistId=uploads_id, maxResults=50)
        if next_page:
            params["pageToken"] = next_page
        res = youtube.playlistItems().list(**params).execute()
        for item in res["items"]:
            videos.append({
                "id":    item["snippet"]["resourceId"]["videoId"],
                "title": item["snippet"]["title"],
            })
        next_page = res.get("nextPageToken")
        if not next_page:
            break

    # 動画ごとの再生数取得
    ranked = []
    for i in range(0, len(videos), 50):
        chunk = videos[i:i+50]
        ids = ",".join(v["id"] for v in chunk)
        vres = youtube.videos().list(part="statistics", id=ids).execute()
        for item in vres["items"]:
            vid = next((v for v in chunk if v["id"] == item["id"]), None)
            if vid:
                ranked.append({
                    "id":    item["id"],
                    "title": vid["title"],
                    "views": int(item["statistics"].get("viewCount", 0)),
                })
    ranked.sort(key=lambda x: x["views"], reverse=True)

    # 収益化達成率（視聴時間はYouTube Analytics APIが必要なため登録者で推定）
    sub_pct  = round(subs / MONETIZE_SUBS * 100, 1)

    report = {
        "date":        datetime.now().strftime("%Y-%m-%d"),
        "subscribers": subs,
        "total_views": total_views,
        "video_count": video_count,
        "top_videos":  ranked[:5],
    }

    # ログ保存
    log = _load_log()
    log.append(report)
    _save_log(log)

    # レポート出力
    sep = "=" * 55
    print(sep)
    print(f"  📊 YouTube Analytics Report  {report['date']}")
    print(sep)
    print(f"  登録者数   : {subs:,} 人  ({sub_pct}% / 収益化まで{max(0, MONETIZE_SUBS-subs):,}人)")
    print(f"  総再生数   : {total_views:,} 回")
    print(f"  動画本数   : {video_count} 本")
    print()
    print("  🏆 再生数ランキング TOP5")
    for i, v in enumerate(ranked[:5], 1):
        title = v["title"][:45] + "…" if len(v["title"]) > 45 else v["title"]
        print(f"  {i}. {title}")
        print(f"     👁 {v['views']:,} 再生")
    print(sep)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    fetch_report()
