#!/usr/bin/env python3
"""
Telegram KOL Daily Brief — 단일 실행(All-in-one) 버전.

매일 텔레그램 국내 KOL 채널을 수집·분석해 Slack에 발행합니다.
이 스크립트는 분석을 Anthropic API로 직접 호출합니다.

  ⚠️  이 방식은 Anthropic API 종량제 크레딧이 필요합니다(ANTHROPIC_API_KEY).
      Claude Code 구독만으로 돌리려면 루틴 방식을 쓰세요:
        fetch_posts.py → (루틴 에이전트가 분석) → publish.py
      자세한 내용은 저장소의 ROUTINE.md 참고.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

import anthropic

from kol_common import (
    KST,
    CHANNELS,
    MAX_ANALYSIS_CHARS,
    fetch_all_channels,
    build_report,
    webhook_post,
)


# ── Claude 분석 ────────────────────────────────────────────────────────────────

ANALYSIS_TOOL = {
    "name": "report_analysis",
    "description": "Korean crypto KOL Telegram post analysis result",
    "input_schema": {
        "type": "object",
        "properties": {
            "key_issues": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "title":          {"type": "string"},
                        "summary_ko":     {"type": "string"},
                        "summary_en":     {"type": "string"},
                        "source_url":     {"type": "string"},
                        "source_channel": {"type": "string"},
                        "has_image":      {"type": "boolean"},
                        "image_url":      {"type": "string"},
                    },
                    "required": ["title", "summary_ko", "summary_en", "source_url", "source_channel"],
                },
            },
            "repeated_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue_name":    {"type": "string"},
                        "channel_count": {"type": "integer"},
                        "channels":      {"type": "array", "items": {"type": "string"}},
                        "keywords":      {"type": "string"},
                        "explanation":   {"type": "string"},
                        "source_urls":   {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                    },
                    "required": ["issue_name", "channel_count", "channels", "keywords", "explanation", "source_urls"],
                },
            },
            "promo_projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string"},
                        "promo_type":   {"type": "string"},
                        "kol_count":    {"type": "integer"},
                        "channels":     {"type": "array", "items": {"type": "string"}},
                        "keywords":     {"type": "string"},
                        "cta_type":     {"type": "string"},
                    },
                    "required": ["project_name", "promo_type", "kol_count", "channels", "keywords", "cta_type"],
                },
            },
            "notable_posts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "url":         {"type": "string"},
                        "channel":     {"type": "string"},
                    },
                    "required": ["description", "url", "channel"],
                },
            },
        },
        "required": ["key_issues", "repeated_issues", "promo_projects", "notable_posts"],
    },
}


def analyze_posts(all_posts: list, total_channels: int, channels_with_posts: int, today_str: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    posts_text = "\n---\n".join(
        f"[{p['channel']}] {p['url']}\n{p['text']}" for p in all_posts
    )[:MAX_ANALYSIS_CHARS]

    prompt = f"""You are a Korean crypto market analyst. Analyze these Telegram posts from Korean crypto KOLs collected on {today_str}.

{posts_text}

Total channels monitored: {total_channels}
Channels with posts today: {channels_with_posts}

Perform this analysis:

1. KEY ISSUES (max 5): Most important market topics.
   - title: Korean title
   - summary_ko: 2-3 sentences in Korean
   - summary_en: 2-3 sentences in English
   - source_url: most influential post URL
   - has_image / image_url: if source post has an image

2. REPEATED ISSUES: Topics mentioned by 5+ different channels.
   Group by theme. Include channel_count, channels list, keywords, one-line explanation, 2-3 source_urls.

3. PROMO PROJECTS: Promotional/ad/airdrop posts grouped by project.
   promo_type: 광고 | 파트너십 | 에어드랍 | 캠페인
   cta_type: 가입 | 예치 | 퀘스트 | 민팅 | 투표 | 기타

4. NOTABLE POSTS: Unusual posts not fitting the above categories."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        tools=[ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "report_analysis"},
        messages=[{"role": "user", "content": prompt}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "report_analysis":
            return block.input

    return None


# ── 메인 ───────────────────────────────────────────────────────────────────────

def main():
    now_kst = datetime.now(KST)
    today_str = now_kst.strftime("%Y-%m-%d")
    cutoff_dt = (now_kst - timedelta(hours=24)).astimezone(timezone.utc)

    print(f"[{today_str}] {len(CHANNELS)}개 채널 수집 시작 (기준: {cutoff_dt.isoformat()})")

    channel_data = asyncio.run(fetch_all_channels(CHANNELS, cutoff_dt))
    channels_with_posts = [c for c in channel_data if c.get("has_posts")]
    all_posts = [
        {**p, "channel": c["channel"]}
        for c in channel_data
        for p in c.get("posts", [])
    ]

    print(f"수집 완료: {len(channels_with_posts)}개 채널 / {len(all_posts)}건 포스트")

    if not all_posts:
        webhook_post(
            os.environ["SLACK_WEBHOOK_URL"],
            {"text": f"오늘은 신규 포스팅이 없습니다 ({today_str})"},
        )
        print("포스트 없음. Slack에 안내 메시지 발행 완료.")
        return

    print("Claude 분석 중...")
    analysis = analyze_posts(all_posts, len(CHANNELS), len(channels_with_posts), today_str)

    if not analysis:
        print("[ERROR] 분석 실패", file=sys.stderr)
        sys.exit(1)

    kor_report = build_report(analysis, len(CHANNELS), today_str, "ko")
    eng_report = build_report(analysis, len(CHANNELS), today_str, "en")

    ki = analysis.get("key_issues", [])
    image_url = None
    if ki and ki[0].get("has_image") and ki[0].get("image_url"):
        image_url = ki[0]["image_url"]

    print("Slack 발행 중...")
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    webhook_post(webhook_url, {"text": kor_report})
    webhook_post(webhook_url, {"text": eng_report})
    if image_url:
        webhook_post(webhook_url, {"text": f"📸 핵심 이슈 이미지: {image_url}"})

    print(
        f"완료! 채널 {len(CHANNELS)}개 모니터링 / "
        f"포스팅 있는 채널 {len(channels_with_posts)}개 / "
        f"총 {len(all_posts)}건 / "
        f"핵심 이슈 {len(ki)}개 / 발행 성공"
    )


if __name__ == "__main__":
    main()
