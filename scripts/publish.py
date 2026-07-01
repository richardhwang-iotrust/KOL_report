#!/usr/bin/env python3
"""
[루틴 3단계] analysis.json(루틴 에이전트가 작성한 분석 결과)을 읽어
한국어·영어 브리핑을 Slack에 발행합니다.

Anthropic API 키가 필요 없습니다. SLACK_WEBHOOK_URL 환경변수만 사용합니다.

입력:
  - posts.json    : 수집 단계 메타데이터 (today, total_channels, posts)
  - analysis.json : 루틴 에이전트가 작성한 분석 결과. 아래 4개 키를 가집니다.
      {
        "key_issues":      [ {title, summary_ko, summary_en, source_url, source_channel, has_image, image_url}, ... ],
        "repeated_issues": [ {issue_name, channel_count, channels, keywords, explanation, source_urls}, ... ],
        "promo_projects":  [ {project_name, promo_type, kol_count, channels, keywords, cta_type}, ... ],
        "notable_posts":   [ {description, url, channel}, ... ]
      }

포스트가 없으면(analysis.json 없음/빈 포스트) "신규 포스팅 없음" 안내만 발행합니다.
"""

import json
import os
import sys
from datetime import datetime

from kol_common import KST, build_report, webhook_post

POSTS_FILE = "posts.json"
ANALYSIS_FILE = "analysis.json"


def _load_json(path: str):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def main():
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    meta = _load_json(POSTS_FILE) or {}
    today_str = meta.get("today") or datetime.now(KST).strftime("%Y-%m-%d")
    total_channels = meta.get("total_channels", 0)
    posts = meta.get("posts", [])

    # 포스트가 없으면 안내 메시지만 발행
    if not posts:
        webhook_post(webhook_url, {"text": f"오늘은 신규 포스팅이 없습니다 ({today_str})"})
        print("포스트 없음. Slack에 안내 메시지 발행 완료.", file=sys.stderr)
        return

    analysis = _load_json(ANALYSIS_FILE)
    if not analysis:
        print(f"[ERROR] {ANALYSIS_FILE} 를 찾을 수 없습니다. 분석 단계를 먼저 수행하세요.",
              file=sys.stderr)
        sys.exit(1)

    kor_report = build_report(analysis, total_channels, today_str, "ko")
    eng_report = build_report(analysis, total_channels, today_str, "en")

    ki = analysis.get("key_issues", [])
    image_url = None
    if ki and ki[0].get("has_image") and ki[0].get("image_url"):
        image_url = ki[0]["image_url"]

    print("Slack 발행 중...", file=sys.stderr)
    webhook_post(webhook_url, {"text": kor_report})
    webhook_post(webhook_url, {"text": eng_report})
    if image_url:
        webhook_post(webhook_url, {"text": f"📸 핵심 이슈 이미지: {image_url}"})

    print(
        f"완료! 채널 {total_channels}개 / 포스팅 {len(posts)}건 / 핵심 이슈 {len(ki)}개 / 발행 성공",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
