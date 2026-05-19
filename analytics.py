"""
YouTubeアナリティクスレポート:
- 総再生数・視聴時間・登録者数を取得
- 収益化条件の達成率を表示
- 上位動画ランキング（直近30日）
"""
import os
import json
import pickle
import logging
from datetime import datetime, date, timedelta
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

REPORT_FILE  = os.path.join(os.path.dirname(__file__), "analytics_log.json")
CLIENT_SECRET = os.path.expanduser("~/Desktop/client_secret.json")
TOKEN_FILE   = os.path.join(os.path.dirname(__file__), "token_analytics.pickle")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

# 収益化条件
MONETIZE_SUBS  = 1000
MONETIZE_HOURS = 4000


def _get_services():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
    youtube   = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)
    return youtube, analytics


def _load_log() -> list:
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE) as f:
            return json.load(f)
    return []


def _save_log(log: list):
    with open(REPORT_FILE, "w") as f:
        json.dump(log[-52:], f, indent=2, ensure_ascii=False)


def fetch_report():
    youtube, analytics = _get_services()

    # チャンネル基本情報
    ch    = youtube.channels().list(part="id,statistics", mine=True).execute()
    item  = ch["items"][0]
    cid   = item["id"]
    stats = item["statistics"]
    subs        = int(stats.get("subscriberCount", 0))
    total_views = int(stats.get("viewCount", 0))
    video_count = int(stats.get("videoCount", 0))

    # 直近30日のアナリティクス
    end_date   = date.today()
    start_date = end_date - timedelta(days=29)
    res = analytics.reports().query(
        ids=f"channel=={cid}",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained",
    ).execute()
    row = res.get("rows", [[0, 0, 0, 0]])[0]
    views_30d   = int(row[0])
    minutes_30d = float(row[1])
    avg_dur_sec = float(row[2])
    subs_30d    = int(row[3])

    # 直近30日・動画別ランキング TOP10
    top_res = analytics.reports().query(
        ids=f"channel=={cid}",
        startDate=start_date.isoformat(),
        endDate=end_date.isoformat(),
        metrics="views,estimatedMinutesWatched",
        dimensions="video",
        sort="-views",
        maxResults=10,
    ).execute()
    top_rows = top_res.get("rows", [])
    top_ids  = [r[0] for r in top_rows]

    # タイトル取得
    titles = {}
    if top_ids:
        vres = youtube.videos().list(part="snippet", id=",".join(top_ids)).execute()
        for v in vres.get("items", []):
            titles[v["id"]] = v["snippet"]["title"]

    # 収益化達成率
    sub_pct   = round(subs / MONETIZE_SUBS * 100, 1)
    hours_30d = minutes_30d / 60

    report = {
        "date":        datetime.now().strftime("%Y-%m-%d"),
        "subscribers": subs,
        "total_views": total_views,
        "video_count": video_count,
        "views_30d":   views_30d,
        "hours_30d":   round(hours_30d, 1),
        "subs_30d":    subs_30d,
    }
    log = _load_log()
    log.append(report)
    _save_log(log)

    sep = "=" * 58
    print(sep)
    print(f"  📊 YouTube Analytics Report  {report['date']}")
    print(sep)
    print(f"  登録者数     : {subs:,} 人  ({sub_pct}% / 収益化まで{max(0, MONETIZE_SUBS-subs):,}人)")
    print(f"  総再生数     : {total_views:,} 回")
    print(f"  動画本数     : {video_count} 本")
    print()
    print(f"  📅 直近30日  ({start_date} → {end_date})")
    print(f"  再生数       : {views_30d:,} 回")
    print(f"  視聴時間     : {hours_30d:,.1f} 時間  (収益化まで{max(0, MONETIZE_HOURS-hours_30d):,.0f}h)")
    print(f"  平均視聴時間 : {avg_dur_sec/60:.1f} 分")
    print(f"  登録者増加   : +{subs_30d} 人")
    print()
    print("  🏆 再生数ランキング TOP10（直近30日）")
    for i, row in enumerate(top_rows, 1):
        vid_id = row[0]
        views  = int(row[1])
        mins   = float(row[2])
        title  = titles.get(vid_id, vid_id)
        title_s = title[:48] + "…" if len(title) > 48 else title
        print(f"  {i:>2}. {title_s}")
        print(f"      👁 {views:,} 再生  ⏱ {mins/60:.1f}h")
    print(sep)

    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    fetch_report()
