# Telegram KOL Daily Brief

국내 암호화폐 KOL(Key Opinion Leader) 텔레그램 채널 **267개**를 매일 자동으로 수집·분석하여 Slack에 데일리 브리핑을 발행하는 프로젝트입니다.

주요 이슈와 시장 동향을 파악하고, KOL을 활용한 프로젝트들의 홍보 내용을 검출해 **고객 후보군 발굴 및 제안영업·협업 제안의 기초자료**로 활용하기 위해 만들었습니다.

## 동작 방식

```
텔레그램 채널 267개  ──▶  수집(스크래핑)  ──▶  Claude 분석  ──▶  Slack 발행
   (t.me/s/<채널>)        최근 24시간 포스트      구조화 요약        한/영 브리핑
```

1. **수집** — `https://t.me/s/<channel>` 공개 미리보기 페이지를 비동기로 크롤링(동시 요청 25개)하여 최근 24시간 내 포스트를 파싱합니다.
2. **분석** — 수집한 포스트를 Claude(`report_analysis` tool)에 전달해 다음 4개 항목으로 구조화합니다.
   - 🔥 **오늘의 핵심 이슈** (최대 5개)
   - 🔁 **중복 언급 이슈** (5개 이상 채널에서 언급된 주제)
   - 📣 **현재 홍보 집중 프로젝트** (광고·파트너십·에어드랍·캠페인)
   - 👀 **특이 포스팅**
3. **발행** — 한국어/영어 두 가지 보고서를 Slack Webhook으로 발행합니다.

## 실행 방식 (두 가지)

분석 단계를 누가 수행하느냐에 따라 **필요한 결제가 다릅니다.**

| 방식 | 분석 주체 | 필요 결제 | 문서 |
|------|-----------|-----------|------|
| **A. Claude Code 루틴** | 루틴의 Claude 에이전트 | claude.ai **구독 사용량만** | [ROUTINE.md](ROUTINE.md) |
| **B. GitHub Actions + API** | 스크립트가 API 직접 호출 | Anthropic **API 종량제 크레딧** | 아래 참고 |

> 💡 Anthropic API 크레딧 없이 이미 결제 중인 구독만으로 돌리려면 **방식 A(루틴)** 를 쓰세요.
> 설정 방법은 [ROUTINE.md](ROUTINE.md)에 정리되어 있습니다.

### 방식 B: GitHub Actions 스케줄

- `.github/workflows/daily_brief.yml`이 **매일 오전 4시(KST) = UTC 19:00**에 `telegram_brief.py`를 실행합니다.
- `workflow_dispatch`로 수동 실행도 가능합니다.
- 이 방식은 `ANTHROPIC_API_KEY`(종량제)와 `SLACK_WEBHOOK_URL`을 리포 Secrets에 등록해야 합니다.

## 프로젝트 구조

```
.
├── scripts/
│   ├── kol_common.py          # 공용: 채널 목록·수집 로직·리포트 생성
│   ├── fetch_posts.py         # [루틴 1단계] 텔레그램 수집 → posts.json (API 키 불필요)
│   ├── publish.py             # [루틴 3단계] analysis.json → Slack 발행 (API 키 불필요)
│   └── telegram_brief.py      # [방식 B] 수집·분석(API)·발행 올인원 스크립트
├── .github/workflows/
│   └── daily_brief.yml        # 방식 B 자동 실행 워크플로우
├── ROUTINE.md                 # 방식 A(Claude 루틴) 설정 가이드
├── requirements.txt           # Python 의존성
└── README.md
```

## 필요 환경변수 (GitHub Secrets)

| 이름 | 설명 |
|------|------|
| `ANTHROPIC_API_KEY` | Claude API 키 |
| `SLACK_WEBHOOK_URL` | 브리핑을 발행할 Slack Incoming Webhook URL |

## 로컬 실행

```bash
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

python scripts/telegram_brief.py
```

## 주요 설정값 (`scripts/telegram_brief.py`)

| 상수 | 기본값 | 설명 |
|------|--------|------|
| `CONCURRENCY` | `25` | 동시 요청 수 |
| `REQUEST_TIMEOUT` | `30` | 채널당 타임아웃(초) |
| `MAX_POST_TEXT` | `600` | 포스트당 최대 문자 수 |
| `MAX_ANALYSIS_CHARS` | `95000` | Claude 입력 최대 문자 수 |

## 의존성

- Python 3.11+
- `anthropic`, `aiohttp`, `beautifulsoup4`
