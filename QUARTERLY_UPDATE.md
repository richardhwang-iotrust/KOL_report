# 분기별 KOL 채널 목록 업데이트

모니터링 채널(`scripts/kol_common.py` 의 `CHANNELS`)을 분기마다 최신 상태로 유지하는 방법입니다.
기준 원본(SSoT)은 **구글시트**이고, 이 시트와 현재 목록을 비교해 **신규(리서치·정보성)는 추가**,
**랭킹에서 빠진 채널은 삭제**, **잡음은 제외**합니다. 최종 반영은 항상 **사람이 검토 후 확정**합니다.

## 관련 파일

| 파일 | 역할 |
|------|------|
| `scripts/kol_common.py` → `CHANNELS` | 현재 모니터링 목록(베이스라인) |
| 구글시트 (순위·채널명·@handle·URL) | 최신 원본(SSoT) — 분기마다 갱신 |
| `scripts/kol_excluded.py` → `EXCLUDED` | 검토 후 '잡음'으로 제외한 채널. **재등장 방지용** |
| `scripts/update_channels.py` | 비교·분류·리포트·(옵션)파일 갱신 도구 |

## 무엇을 하나

1. 시트 − (CHANNELS ∪ EXCLUDED) = **신규 후보**
2. 신규 후보를 **리서치·정보성(추가 추천)** / **보류(잡음·판단필요)** 로 1차 자동 분류(키워드)
   - 포함 신호: research·리서치·리포트·뉴스·데이터·온체인·정보방·정리·아카이브·insight·공부·교실·차트 …
   - 제외 신호: 일기·낙서·메모·폐지·에어드랍·에드작·뿌리기·기브·도박·리딩방·쓰레기통 …
   - 애매하면 **보류**(사람이 최종 판단)
3. CHANNELS − 시트 = **랭킹 이탈**(삭제 후보)
4. `channel_update_report.md` 리포트 출력

> 자동 분류는 1차 참고용입니다. add/exclude 최종 결정은 사람이 합니다.

## 방식 A — GitHub Actions (권장, PR로 검토)

`.github/workflows/quarterly_update.yml` 이 **매 분기 첫날 10시(KST)** 실행되어
변경을 적용한 **PR을 자동으로 올립니다.** 사람은 PR의 리포트와 diff를 보고 머지/수정만 하면 됩니다.
Anthropic API 키가 필요 없습니다.

설정(최초 1회):
1. **Settings → Secrets and variables → Actions → Variables** 에 `KOL_SHEET_ID` 등록
   (구글시트 URL 의 `/d/` 와 `/edit` 사이 ID). 시트는 *링크가 있는 모든 사용자 보기 가능* 이어야 CSV export 가 열립니다.
2. **Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests"** 체크.
3. 즉시 시험은 Actions 탭에서 **Run workflow**(`workflow_dispatch`).

## 방식 B — 로컬 / 수동

```bash
# 미리보기(파일 수정 없음)
python scripts/update_channels.py --sheet "https://docs.google.com/spreadsheets/d/<ID>/export?format=csv"

# 실제 적용 후 직접 커밋·PR
python scripts/update_channels.py --sheet <CSV_URL_또는_로컬.csv> --apply
git checkout -b chore/quarterly-kol-update
git add scripts/kol_common.py scripts/kol_excluded.py
git commit -m "chore: 분기 KOL 채널 목록 업데이트"
```

`--apply` 는 CHANNELS 에 '추가 추천'을 넣고 이탈 채널을 빼며, '보류'는 `kol_excluded.py` 에 누적합니다.

## 방식 C — Claude Code 루틴 (판단까지 위임)

키워드 분류가 아니라 **에이전트의 판단**으로 큐레이션하고 싶으면, 분기 1회 루틴에 아래를 넣습니다.

```
분기 KOL 채널 갱신을 수행해줘.
1) python scripts/update_channels.py --sheet "<시트 CSV export URL>"  로 신규/이탈/보류를 뽑는다.
2) '보류'로 분류된 후보를 채널명 기준으로 다시 판단해, 리서치·정보성이면 살리고 잡음이면 제외한다.
3) 확정한 목록으로 kol_common.py 의 CHANNELS 를 수정하고, 제외분은 kol_excluded.py 에 누적한다.
4) 변경 요약을 남기고, 커밋·PR 은 만들지 말고 내가 검토하도록 diff 만 보여줘.
```

## 제외한 채널을 다시 넣고 싶으면

`scripts/kol_excluded.py` 의 `EXCLUDED` 에서 해당 핸들을 지우면, 다음 실행에서 신규 후보로 다시 올라옵니다.
