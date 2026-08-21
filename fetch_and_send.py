#!/usr/bin/env python3
""" 
매일 아침 최신 IT 트렌드를 수집해서 Slack으로 전송합니다.

수집 소스:
  - Hacker News 상위 스토리
  - 지정 RSS 피드 (기본: TechCrunch, The Verge)

환경 변수:
  SLACK_WEBHOOK_URL  (필수) Slack Incoming Webhook URL
  HN_TOP_N           (선택) Hacker News에서 가져올 상위 스토리 수 (기본: 5)
  RSS_TOP_N          (선택) RSS 피드에서 가져올 상위 기사 수 (기본: 3)
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests
import feedparser

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
HN_TOP_N = int(os.getenv("HN_TOP_N", 5))
RSS_TOP_N = int(os.getenv("RSS_TOP_N", 3))

RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
]

HN_BASE = "https://hacker-news.firebaseio.com/v0"

def fetch_hacker_news(top_n: int) -> list[dict]:
    """Hacker News 상위 스토리를 가져온다."""
    try:
        story_ids = requests.get(f"{HN_BASE}/topstories.json", timeout=15).json()
        items = []
        for sid in story_ids[:top_n]:
            r = requests.get(f"{HN_BASE}/item/{sid}.json", timeout=15)
            data = r.json()
            if not data:
                continue
            items.append({
                "title": data.get("title", "(제목 없음)"),
                "url": data.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                "score": data.get("score", 0),
                "source": "Hacker News",
            })
            time.sleep(0.2)  # API 부하 방지
        return items
    except Exception as e:
        print(f"[WARN] Hacker News 수집 실패: {e}", file=sys.stderr)
        return []

def fetch_rss_feeds(feeds: list[str], per_feed: int) -> list[dict]:
    """RSS 피드들을 파싱해서 최신 항목을 가져온다."""
    items = []
    for url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:per_feed]:
                items.append({
                    "title": entry.get("title", "(제목 없음)"),
                    "url": entry.get("link", ""),
                    "source": parsed.feed.get("title", url),
                })
        except Exception as e:
            print(f"[WARN] RSS 피드 수집 실패 ({url}): {e}", file=sys.stderr)
    return items

def build_slack_message(hn_items: list[dict], rss_items: list[dict]) -> dict:
    """Slack Block Kit 메시지를 구성한다."""
    kst = timezone(timedelta(hours=9))
    today = datetime.now(kst).strftime("%Y-%m-%d")
    
    blocks = [
        {
            "type": "header", 
            "text": {"type": "plain_text", "text": f"🌅 IT 트렌드 - ({today})"}},
        {"type": "divider"},
    ]

    if hn_items:
        blocks.append({
            "type": "section", 
            "text": {"type": "mrkdwn", "text": "*🔥 Hacker News 상위*"}})
        for i, item in enumerate(hn_items, start=1):
            score = item.get("score")
            score_str = f" ({score}pt)" if score is not None else ""
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i}. <{item['url']}|{item['title']}>{score_str}",
                },
            })

    if rss_items:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📰 주요 IT 뉴스*"}
        })
        for i, item in enumerate(rss_items, start=1):
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i}. <{item['url']}|{item['title']}>\n _{item['source']}_",
                }
            })
    if not hn_items and not rss_items:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "오늘 수집된 항목이 없습니다 🤔"}
        })
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {"type": "plain_text", "text": "자동 수집 봇 - Github Actions | 데이터 출처: Hacker News, RSS 피드"}]
    })
    return {"blocks": blocks}

def send_to_slack(message: dict) -> None:
    """ Slack Webhook으로 메시지를 전송한다. """
    if not SLACK_WEBHOOK_URL:
        print("[ERROR] SLACK_WEBHOOK_URL 환경 변수가 설정되지 않았습니다.", file=sys.stderr)
        sys.exit(1)    
    
    resp = requests.post(
        SLACK_WEBHOOK_URL,
        data=json.dumps(message),
        headers={"Content-Type": "application/json"},
        timeout=15
    )

    if resp.status_code != 200 or resp.text != "ok":
        print(f"[ERROR] Slack 전송 실패: {resp.status_code} - {resp.text}", file=sys.stderr)
        sys.exit(1)
    print("✅ Slack 전송 완료")

def main() -> None:
    print("⏳ IT 트렌드 수집 시작...")
    hn_items = fetch_hacker_news(HN_TOP_N)
    rss_items = fetch_rss_feeds(RSS_FEEDS, RSS_TOP_N)
    print(f"✅ 수집 완료: Hacker News {len(hn_items)}개, RSS {len(rss_items)}개")

    message = build_slack_message(hn_items, rss_items)
    send_to_slack(message)

if __name__ == "__main__":
    main()