#!/usr/bin/env python3
"""
분기별 KOL 채널 리스트 업데이트 도구.

대상 파일:
  - scripts/kol_common.py 의 CHANNELS      → 현재 모니터링 목록(베이스라인)
  - Google Sheet (CSV export)              → 최신 원본(SSoT): 순위,채널명,@handle,URL
  - scripts/kol_excluded.py 의 EXCLUDED    → 이전 검토에서 '잡음'으로 제외한 채널
                                             (재등장 방지 / 없으면 빈 목록으로 간주)

동작:
  1) 시트 − (CHANNELS ∪ EXCLUDED) = 신규 후보
  2) 신규 후보를 '리서치·정보성' / '보류(잡음·판단필요)'로 1차 자동 분류(키워드)
     → 최종 확정은 사람이 PR에서 검토
  3) CHANNELS − 시트 = 랭킹 이탈(삭제 후보)
  4) channel_update_report.md 리포트 출력
  5) --apply 지정 시:
       · CHANNELS 에 '리서치·정보성' 후보 추가 + 이탈 채널 삭제 → kol_common.py 갱신
       · '보류'로 분류된 후보는 kol_excluded.py 에 누적 → 다음 분기 재등장 방지
     (자동 커밋은 하지 않는다. GitHub Actions 워크플로우가 PR로 올린다.)

사용 예:
  python scripts/update_channels.py --sheet "https://docs.google.com/spreadsheets/d/<ID>/export?format=csv"
  python scripts/update_channels.py --sheet channels_sheet.csv --apply
"""
import argparse
import ast
import csv
import io
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
KOL_COMMON = os.path.join(HERE, "kol_common.py")
EXCLUDED_FILE = os.path.join(HERE, "kol_excluded.py")
REPORT = os.path.join(os.path.dirname(HERE), "channel_update_report.md")

# ── 1차 자동 분류 키워드 (최종 판단은 사람) ──────────────────────────────────
INCLUDE_KW = [
    "research", "리서치", "리포트", "report", "뉴스", "news", "데이터", "data",
    "온체인", "onchain", "정보방", "정보공유", "정보 나눔", "정리", "노트", "note",
    "아카이브", "archive", "idea", "insight", "인사이트", "공부", "study", "교실",
    "class", "클래스", "analytics", "차트", "chart", "애널", "dashboard", "feed",
    "aggr", "labs", "lab",
]
EXCLUDE_KW = [
    "일기", "diary", "dairy", "낙서", "메모", "memo", "폐지", "에어드랍", "에드작",
    "airdrop", "뿌리", "막퍼", "기브", "giveaway", "도박", "베팅", "gamble",
    "betting", "쓰레기통", "trash", "딸깍", "존버", "리딩방",
]


def norm(h: str) -> str:
    return h.lstrip("@").strip().lower()


def load_channels() -> list:
    """kol_common.py 에서 CHANNELS 리스트를 텍스트 파싱(임포트 부작용 회피)."""
    src = open(KOL_COMMON, encoding="utf-8").read()
    m = re.search(r"CHANNELS\s*=\s*(\[.*?\])", src, re.DOTALL)
    if not m:
        sys.exit("ERROR: kol_common.py 에서 CHANNELS 리스트를 찾지 못했습니다.")
    return ast.literal_eval(m.group(1))


def load_excluded() -> list:
    if not os.path.exists(EXCLUDED_FILE):
        return []
    src = open(EXCLUDED_FILE, encoding="utf-8").read()
    m = re.search(r"EXCLUDED\s*=\s*(\[.*?\])", src, re.DOTALL)
    return ast.literal_eval(m.group(1)) if m else []


def read_sheet(src: str) -> list:
    """구글시트 CSV(순위,채널명,@handle,URL) → [(name, handle)] 순서 보존."""
    if src.startswith("http"):
        with urllib.request.urlopen(src, timeout=30) as r:
            text = r.read().decode("utf-8")
    else:
        text = open(src, encoding="utf-8").read()
    rows = list(csv.reader(io.StringIO(text)))
    out, seen = [], set()
    for r in rows[1:]:
        if len(r) < 3:
            continue
        name, handle = r[1].strip(), norm(r[2])
        if not handle or handle in seen:
            continue
        seen.add(handle)
        out.append((name, handle))
    return out


def classify(name: str, handle: str) -> str:
    blob = (name + " " + handle).lower()
    if any(k in blob for k in EXCLUDE_KW):
        return "보류"
    if any(k in blob for k in INCLUDE_KW):
        return "추가"
    return "보류"  # 애매하면 보류 — 사람이 최종 판단


def rewrite_channels(new_list: list):
    src = open(KOL_COMMON, encoding="utf-8").read()
    lines = ["CHANNELS = ["]
    for i in range(0, len(new_list), 5):
        chunk = ", ".join(f'"{h}"' for h in new_list[i:i + 5])
        lines.append(f"    {chunk},")
    lines.append("]")
    block = "\n".join(lines)
    new_src = re.sub(r"CHANNELS\s*=\s*\[.*?\]", block, src, count=1, flags=re.DOTALL)
    open(KOL_COMMON, "w", encoding="utf-8").write(new_src)


def write_excluded(handles: list):
    handles = sorted(set(handles), key=str.lower)
    lines = [
        "# 분기 검토에서 '잡음'으로 제외한 채널 (재등장 방지용).",
        "# 다시 모니터링하려면 해당 핸들을 여기서 지우고 kol_common.py CHANNELS 에 추가하세요.",
        "EXCLUDED = [",
    ]
    for i in range(0, len(handles), 5):
        lines.append("    " + ", ".join(f'"{h}"' for h in handles[i:i + 5]) + ",")
    lines.append("]")
    open(EXCLUDED_FILE, "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True, help="구글시트 CSV export URL 또는 로컬 CSV 경로")
    ap.add_argument("--apply", action="store_true", help="kol_common.py / kol_excluded.py 실제 수정")
    args = ap.parse_args()

    channels = load_channels()
    excluded = load_excluded()
    sheet = read_sheet(args.sheet)

    chan_set = {norm(h) for h in channels}
    excl_set = {norm(h) for h in excluded}
    sheet_map = {h: n for n, h in sheet}          # handle -> name
    sheet_order = [h for _, h in sheet]

    new_cand = [h for h in sheet_order if h not in chan_set and h not in excl_set]
    departed = [h for h in channels if norm(h) not in sheet_map]

    add, hold = [], []
    for h in new_cand:
        (add if classify(sheet_map[h], h) == "추가" else hold).append(h)

    # ── 리포트 ──
    q = ""
    r = ["# 분기 KOL 채널 업데이트 리포트\n",
         f"- 현재 모니터링: **{len(channels)}개**   /   시트(SSoT): **{len(sheet)}개**   /   기존 제외목록: **{len(excluded)}개**",
         f"- 신규 후보: **{len(new_cand)}**  (추가 추천 {len(add)} · 보류 {len(hold)})   /   랭킹 이탈: **{len(departed)}**\n",
         "## ✅ 추가 추천 (리서치·정보성)"]
    r += [f"- {sheet_map[h]} — https://t.me/{h}" for h in add] or ["- (없음)"]
    r += ["\n## ⏸ 보류 (잡음·판단필요 → 사람 검토)"]
    r += [f"- {sheet_map[h]} — https://t.me/{h}" for h in hold] or ["- (없음)"]
    r += ["\n## 🗑 랭킹 이탈 (삭제 후보)"]
    r += [f"- https://t.me/{h}" for h in departed] or ["- (없음)"]
    r += ["\n> 자동 분류는 1차 참고용입니다. 최종 add/exclude 는 PR 리뷰에서 사람이 확정하세요."]
    report = "\n".join(r) + "\n"
    open(REPORT, "w", encoding="utf-8").write(report)
    print(report)

    if args.apply:
        keep = [h for h in channels if norm(h) in sheet_map]  # 이탈 제거
        keep += add                                            # 추천 추가
        rewrite_channels(keep)
        write_excluded(excluded + hold)                        # 보류 누적
        print(f"[applied] CHANNELS {len(channels)} → {len(keep)} · EXCLUDED +{len(hold)}")
    else:
        print("[dry-run] --apply 를 붙이면 kol_common.py / kol_excluded.py 를 실제 수정합니다.")


if __name__ == "__main__":
    main()
