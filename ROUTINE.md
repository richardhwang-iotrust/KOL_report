# Claude Code 루틴으로 자동실행하기

이 문서는 **Anthropic API 종량제 크레딧 없이**, 이미 결제 중인 **Claude Code 구독**만으로
데일리 브리핑을 매일 자동 발행하도록 설정하는 방법입니다.

## 왜 이 방식인가

| | GitHub Actions + API 키 | **Claude Code 루틴 (이 문서)** |
|---|---|---|
| 분석 주체 | 스크립트가 Anthropic **API 직접 호출** | 루틴의 **Claude 에이전트가 직접 분석** |
| 필요 결제 | Anthropic API 종량제 크레딧 ❌ | claude.ai 구독 사용량만 ✅ |

루틴은 **Claude Code 세션을 하나 실행**하고, 그 세션의 Claude가 분석을 수행합니다.
따라서 `ANTHROPIC_API_KEY`가 전혀 필요 없습니다.

> 참고: 루틴은 Pro/Max/Team/Enterprise 플랜 + Claude Code on the web에서 사용 가능하며,
> **계정당 일일 실행 횟수 상한**과 구독 사용량 한도가 적용됩니다.

## 실행 흐름

```
1) fetch_posts.py   (파이썬)  → posts.json 생성        [API 키 불필요]
2) 분석             (Claude)  → analysis.json 작성     [구독 사용]
3) publish.py       (파이썬)  → Slack 발행             [SLACK_WEBHOOK_URL만 필요]
```

## 설정 절차

### 1. 루틴 생성
[claude.ai/code/routines](https://claude.ai/code/routines) → **New routine** (또는 CLI에서 `/schedule`).

- **Repository**: 이 저장소 선택
- **Schedule**: `Daily` (원하면 `/schedule update`로 정확한 cron 지정 — 매일 KST 04시 = `0 19 * * *`)
- **Model**: Claude 최신 모델 선택

### 2. 환경(Environment) 설정
루틴 편집 화면에서 환경을 고르고 다음을 설정합니다.

- **Network access**: `Custom` 으로 두고 **Allowed domains**에 아래 추가
  - `t.me` (텔레그램 수집)
  - `hooks.slack.com` (Slack 발행)
  - "기본 패키지 매니저 목록 포함" 체크 (pip 설치용)
- **Environment variables**:
  - `SLACK_WEBHOOK_URL` = Slack Incoming Webhook URL
- **Setup script** (선택, 의존성 캐시용):
  ```bash
  pip install -r requirements.txt
  ```

### 3. 루틴 프롬프트

아래 내용을 그대로 붙여넣으세요.

```
당신은 한국 암호화폐 시장 애널리스트입니다. 다음 순서로 데일리 브리핑을 발행하세요.

1. 의존성 설치:
   pip install -r requirements.txt

2. 텔레그램 포스트 수집:
   python scripts/fetch_posts.py
   → posts.json 이 생성됩니다.

3. posts.json 을 읽으세요. "posts" 배열이 비어 있으면 4단계(분석)를 건너뛰고 바로 5단계로 가세요.

4. posts.json 의 포스트들을 분석해 아래 4개 항목을 만들고, 그 결과를 analysis.json 파일로 저장하세요.
   JSON 최상위 키는 정확히 key_issues, repeated_issues, promo_projects, notable_posts 여야 합니다.

   - key_issues (최대 5개): 가장 중요한 시장 이슈.
     각 항목: title(한국어 제목), summary_ko(한국어 2~3문장), summary_en(영어 2~3문장),
     source_url(가장 영향력 있는 포스트 URL), source_channel, has_image(bool), image_url
   - repeated_issues: 서로 다른 5개 이상 채널에서 언급된 주제. 테마별로 묶기.
     각 항목: issue_name, channel_count(정수), channels(배열), keywords, explanation(한 줄), source_urls(최대 3개)
   - promo_projects: 광고/에어드랍/홍보 포스트를 프로젝트별로 묶기.
     각 항목: project_name, promo_type(광고|파트너십|에어드랍|캠페인), kol_count(정수), channels(배열),
     keywords, cta_type(가입|예치|퀘스트|민팅|투표|기타)
   - notable_posts: 위 분류에 안 맞는 특이 포스트. 각 항목: description, url, channel

5. Slack 발행:
   python scripts/publish.py
   (posts.json 의 포스트가 없으면 "신규 포스팅 없음" 안내가 자동 발행됩니다.)

작업이 끝나면 발행 결과를 한 줄로 요약해 보고하세요. 커밋이나 PR은 만들지 마세요.
```

### 4. 저장 후 확인
- **Run now** 로 즉시 한 번 실행해 Slack에 정상 발행되는지 확인합니다.
- 이후에는 매일 스케줄에 맞춰 자동 실행됩니다.

## 참고: analysis.json 스키마

`publish.py`가 기대하는 형식입니다. (프롬프트의 4단계와 동일)

```json
{
  "key_issues":      [{ "title": "...", "summary_ko": "...", "summary_en": "...",
                        "source_url": "...", "source_channel": "...",
                        "has_image": true, "image_url": "..." }],
  "repeated_issues": [{ "issue_name": "...", "channel_count": 7, "channels": ["..."],
                        "keywords": "...", "explanation": "...", "source_urls": ["..."] }],
  "promo_projects":  [{ "project_name": "...", "promo_type": "에어드랍", "kol_count": 5,
                        "channels": ["..."], "keywords": "...", "cta_type": "퀘스트" }],
  "notable_posts":   [{ "description": "...", "url": "...", "channel": "..." }]
}
```
