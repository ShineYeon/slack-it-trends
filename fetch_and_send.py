#!/usr/bin/env python3
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import requests
import feedparser
# 🌟 무료 번역 라이브러리 추가
from deep_translator import GoogleTranslator 

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
HN_TOP_N = int(os.getenv("HN_TOP_N", 5))
RSS_TOP_N = int(os.getenv("RSS_TOP_N", 3))

RSS_FEEDS = [
    "https://hada.io",       # 국내 최고 개발자 커뮤니티 (GeekNews)
    "https://tldr.tech",       # 글로벌 최신 AI 트렌드 요약 (TLDR AI)
]

HN_BASE = "https://hacker-news.firebaseio.com/v0"

# 🌟 [신규 함수] 영문 제목을 한글 짧은 요약으로 번역하는 유틸리티
def translate_to_ko(text: str) -> str:
    try:
        if not text or text.isspace():
            return ""
        # 구글 번역기를 이용해 영어를 한국어로 변환합니다.
        translated = GoogleTranslator(source='en', target='ko').translate(text)
        return translated
    except Exception as e:
        print(f"[WARN] 번역 실패: {e}", file=sys.stderr)
        return text # 번역 실패 시 원문 유지

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
                
            orig_title = data.get("title", "(제목 없음)")
            print(f"  - HN 파싱 및 번역 중: {orig_title[:30]}...")
            # 🌟 번역 요약본 생성
            ko_summary = translate_to_ko(orig_title)

            items.append({
                "title": orig_title,
                "ko_summary": ko_summary, # 🌟 추가
                "url": data.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                "score": data.get("score", 0),
                "source": "Hacker News",
            })
            time.sleep(0.2)
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
                orig_title = entry.get("title", "(제목 없음)")
                print(f"  - RSS 파싱 및 번역 중: {orig_title[:30]}...")
                # 🌟 번역 요약본 생성
                ko_summary = translate_to_ko(orig_title)

                items.append({
                    "title": orig_title,
                    "ko_summary": ko_summary, # 🌟 추가
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
            "text": {"type": "plain_text", "text": f"🌅 IT 트렌드 한글 요약 - ({today})"}},
        {"type": "divider"},
    ]

    if hn_items:
        blocks.append({
            "type": "section", 
            "text": {"type": "mrkdwn", "text": "*🔥 Hacker News 상위*"}})
        for i, item in enumerate(hn_items, start=1):
            score = item.get("score")
            score_str = f" ({score}pt)" if score is not None else ""
            # 🌟 슬랙 메시지 구조 변경: 원문 링크 하단에 한글 요약 한 줄 배치
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i}. <{item['url']}|{item['title']}>{score_str}\n👉 *한글 요약:* _{item['ko_summary']}_",
                },
            })

    if rss_items:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*📰 주요 IT 뉴스*"}
        })
        for i, item in enumerate(rss_items, start=1):
            # 🌟 슬랙 메시지 구조 변경: 원문 링크 하단에 한글 요약 한 줄 배치
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{i}. <{item['url']}|{item['title']}>\n👉 *한글 요약:* _{item['ko_summary']}_\n _출처: {item['source']}_",
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
            {"type": "plain_text", "text": "자동 수집 및 한글 요약 봇 - Github Actions | 데이터 출처: Hacker News, RSS"}]
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
    print("⏳ IT 트렌드 및 번역 수집 시작...")
    hn_items = fetch_hacker_news(HN_TOP_N)
    rss_items = fetch_rss_feeds(RSS_FEEDS, RSS_TOP_N)
    print(f"✅ 수집 및 번역 완료: Hacker News {len(hn_items)}개, RSS {len(rss_items)}개")

    message = build_slack_message(hn_items, rss_items)
    send_to_slack(message)

if __name__ == "__main__":
    main()
