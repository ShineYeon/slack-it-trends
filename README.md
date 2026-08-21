# IT Trends to Slack

매일 아침 9시(한국 시간)에 최신 IT 트렌드를 수집해서 Slack으로 전송합니다.

## 동작

1. Hacker News 상위 스토리 수집
2. 지정 RSS 피드(기본: TechCrunch, The Verge) 수집
3. 항목 정리 후 Slack Incoming Webhook으로 전송
4. Github Actions cron(UTC 00:00 = KST 09:00)으로 매일 실행

## 설정 (Github Secret) 등록

리포지토리 Settings -> Secrets and variables -> Actions에 다음 추가:

| Secret 이름 | 값 |                                                     
|--------------|----|                                                    
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL | 

Slack Webhook URL 발급:
1. https://api.slack.com/apps 접속 -> Create New App -> From scratch(Blank app)
2. 앱 이름 입력, 워크 스페이스 선택 -> Create App
3. 좌측 Incoming Webhooks -> Activate On
4. Add New Webhook to Workspace -> 채널 선택 -> Authorize
5. Webhook URL 복사 -> Github Secret에 등록

## 로컬 테스트

export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
python fetch_and_send.py

## RSS 피드 추가

`fetch_and_send.py`의 `RSS_FEEDS` 목록에 URL 추가.