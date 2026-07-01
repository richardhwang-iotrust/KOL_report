# Claude Code 루틴으로 자동실행하기

이 문서는 **Anthropic API 종량제 크레딧 없이**, 이미 결제 중인 **Claude Code 구독**만으로
데일리 브리핑을 매일 자동 발행하도록 설정하는 방법입니다. (검증 완료된 최종 버전)

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
1) fetch_posts.py (파이썬)  → posts.json 생성            [API 키 불필요]
2) 분석          (Claude)   → 핵심/중복/홍보/특이 정리    [구독 사용]
3) 발행          (Claude)   → Slack #info-telegram_test  [Slack 커넥터]
   · 한국어 본문 게시 → 영어판을 그 글의 댓글(스레드)로 게시
   · 핵심 이슈 이미지가 있으면 원문 텔레그램 URL을 함께 표시
```

수집은 스크립트가 빠르고 확실하게(전체 채널 ~10초) 처리하고, 분석·발행은 에이전트가 담당합니다.

## 설정 절차

### 1. 루틴 생성 / 수정
이미 "텔레그램 엿보기 봇" 루틴이 있다면 **새로 만들지 말고 그 프롬프트만 교체**하세요.
- [claude.ai/code/routines](https://claude.ai/code/routines) → 루틴 선택 → 연필(Edit)
- 없으면 **New routine** (또는 CLI `/schedule`)

- **Repository**: 이 저장소 (`richardhwang-iotrust/KOL_report`), 최신 `main` 복제
- **Schedule**: `Daily` (정확히 KST 04시로 맞추려면 `/schedule update`로 cron `0 19 * * *`)
- **Model**: Claude 최신 모델

### 2. 환경(Environment) 설정
- **Network access**: `Custom` — 허용 도메인에 아래 추가 + "기본 패키지 매니저 목록 포함" 체크
  - `t.me` (텔레그램 수집)
  - (Slack 커넥터 트래픽은 Anthropic 서버 경유라 별도 도메인 허용 불필요)
- **Connectors**: **Slack 커넥터 ON** (`#info-telegram_test` 게시·스레드 댓글용)
- 환경변수: 이 방식에서는 `ANTHROPIC_API_KEY`·`SLACK_WEBHOOK_URL` 모두 **불필요**

### 3. 루틴 프롬프트 (그대로 복사)

```
매일 아침, scripts/fetch_posts.py 로 수집한 국내 텔레그램 공개 채널들의
최근 24시간 포스팅을 분석해 사내 데일리 브리핑을 만들고
Slack #info-telegram_test 채널에 발행한다.

[작업 순서]
0. 의존성 설치: pip install -r requirements.txt

1. 수집: python scripts/fetch_posts.py
   → posts.json 이 생성된다. (today, total_channels, channels_with_posts,
     posts[{channel, url, text, date, has_image, image_url}] 포함)
   posts.json 의 "posts" 가 비어 있으면 "오늘은 신규 포스팅이 없습니다" 한 줄만
   Slack #info-telegram_test 에 남기고 종료한다.

2. posts.json 을 읽어 분석한다:
   - 핵심 이슈: 오늘 가장 중요한 주제 최대 5개
   - 중복 언급 이슈: 서로 다른 5개 이상 채널이 비슷한 주제를 다룬 경우 하나로 묶고,
     언급 채널 수 / 대표 키워드 / 대표 원문 링크 2~3건 / 해설을 적는다
   - 홍보성 프로젝트: 광고·파트너십·캠페인·에어드랍 유도 글을 프로젝트 단위로 묶고,
     언급 KOL 수 / 홍보 유형 / 반복 키워드 / CTA 유형(가입·예치·퀘스트·민팅 등)을 적는다
   - 특이 포스팅: 위에 안 들지만 주목할 글
   ※ 각 항목의 설명은 한국어 기준 100자 내외(2~3문장)로, 제목만 보고도 배경과
     맥락이 이해되도록 충분히 작성한다. 한 줄로 너무 짧게 줄이지 않는다.
   링크는 구독자수 기준 가장 영향력 있는 텔레그램 원문 링크를 쓴다.

3. 한국어판·영어판 요약 보고서 2종을 작성한다. 형식:

   *📡 텔레그램 KOL 모니터링 데일리 브리핑* — YYYY-MM-DD
   이 게시물은 최근 24시간동안 텔레그램 국내 탑 <모니터링 갯수>개의 KOL들의 포스팅을 분석 요약한 보고서입니다.
   주요 이슈와 동향파악 및 KOL을 이용한 프로젝트들의 홍보내용을 검출해서 고객 후보군을 발굴하여 제안영업이나 협업 제안의 기초자료로 사용하기 위해 만들었습니다.

   *🔥 오늘의 핵심 이슈*
   • *<제목>* — <100자 내외 요약>  출처: <링크>
   *🔁 중복 언급 이슈*
   • *<이슈명>* (N개 채널 언급) — <100자 내외 해설>  키워드: ...  출처: <링크>
   *📣 현재 홍보 집중 프로젝트*
   • *<프로젝트명>* — <홍보 유형> (N KOL, CTA: <유형>) — <100자 내외 설명>
   *👀 특이 포스팅*
   • <100자 내외 설명>  <링크>

   영어판은 동일 구조에 제목만 영문: Telegram Daily Brief / Top Market Topics Today /
   Repeated Cross-KOL Issues / Projects Currently Being Promoted / Notable Posts.
   해당 항목이 없으면 "(해당 없음)" / "(none)".

4. Slack #info-telegram_test 채널에 한국어 보고서를 게시하고,
   영어 보고서는 그 글의 댓글(스레드)로 게시한다.

5. 핵심 이슈 첫 번째 항목의 원문 포스트에 이미지가 있으면(posts.json 의 has_image/image_url),
   그 이미지가 포함된 텔레그램 원문 URL을 한국어 메시지 맨 아래에
   "🖼 핵심 이슈 원문(이미지 포함): <URL>" 형태로 함께 보여준다.
   (Slack 파일 업로드가 가능한 환경이면 이미지를 직접 첨부해도 된다.)

6. 마지막에 수집 채널 수 / 분석한 글 수 / 핵심 이슈 수 / 발행 성공 여부를 2~3줄로 요약한다.
   커밋이나 PR은 만들지 않는다.
```

### 4. 저장 후 확인
- **Run now** 로 즉시 실행 → `#info-telegram_test` 에 한국어 본문 + 영어 댓글 + 이미지 원문 URL이 정상 발행되는지 확인
- 이후 매일 스케줄에 맞춰 자동 실행

## 채널 추가/삭제
모니터링 채널은 프롬프트가 아니라 **`scripts/kol_common.py` 의 `CHANNELS` 리스트**에서 관리합니다.
채널을 추가/삭제하려면 이 리스트만 수정하면 됩니다. (현재 267개)

## 참고: Slack webhook 대안 (`publish.py`)
스레드 댓글·이미지 없이 **webhook으로 단순 발행**만 원하면, 분석 결과를 `analysis.json`
(키: `key_issues`, `repeated_issues`, `promo_projects`, `notable_posts`)로 저장한 뒤
`python scripts/publish.py` 를 실행하면 됩니다. 이 경로는 `SLACK_WEBHOOK_URL` 환경변수만 사용하며,
영어판은 스레드가 아닌 별도 메시지로, 이미지는 URL 텍스트로 발행됩니다.
