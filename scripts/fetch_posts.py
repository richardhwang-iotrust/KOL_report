#!/usr/bin/env python3
"""
[루틴 1단계] 텔레그램 국내 KOL 채널들의 최근 24시간 포스트를 수집해 posts.json으로 저장합니다.

Anthropic API 키가 필요 없습니다. (분석은 이후 Claude Code 루틴 에이전트가 수행)

출력: posts.json
{
  "today": "2026-07-01",
  "total_channels": 267,
  "channels_with_posts": 42,
  "posts": [ {channel, url, text, date, has_image, image_url}, ... ]
}
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone

from kol_common import KST, CHANNELS, fetch_all_channels

OUTPUT_FILE = "posts.json"


def main():
    now_kst = datetime.now(KST)
    today_str = now_kst.strftime("%Y-%m-%d")
    cutoff_dt = (now_kst - timedelta(hours=24)).astimezone(timezone.utc)

    print(f"[{today_str}] {len(CHANNELS)}개 채널 수집 시작 (기준: {cutoff_dt.isoformat()})",
          file=sys.stderr)

    channel_data = asyncio.run(fetch_all_channels(CHANNELS, cutoff_dt))
    channels_with_posts = [c for c in channel_data if c.get("has_posts")]
    all_posts = [
        {**p, "channel": c["channel"]}
        for c in channel_data
        for p in c.get("posts", [])
    ]

    out = {
        "today": today_str,
        "total_channels": len(CHANNELS),
        "channels_with_posts": len(channels_with_posts),
        "posts": all_posts,
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(
        f"수집 완료: {len(channels_with_posts)}개 채널 / {len(all_posts)}건 포스트 → {OUTPUT_FILE}",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
