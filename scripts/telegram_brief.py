#!/usr/bin/env python3
"""
Telegram KOL Daily Brief
매일 오전 4시(KST) 텔레그램 국내 KOL 채널 267개를 수집·분석해 Slack에 발행합니다.
"""

import asyncio
import aiohttp
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
import anthropic

# ── 설정 ───────────────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
SLACK_CHANNEL = "C0B5H4AAN02"
CONCURRENCY = 25          # 동시 요청 수
REQUEST_TIMEOUT = 20      # 채널당 타임아웃(초)
MAX_POST_TEXT = 600       # 포스트당 최대 문자 수
MAX_ANALYSIS_CHARS = 95000  # Claude 입력 최대 문자

CHANNELS = [
    "twitchoong","seaotterbtc","emperorcoin","moneybottle","CryptoFamily_ilhyun",
    "WeCryptoTogether","SUS_secretnote","officialunivercityofcrypto","jerryview",
    "JoshuaDeukKOR","GODOGtrader","Thoughts_BFox","BChoSN","icoroots","dontak00",
    "enjoymyhobby","crypto_fundraising","murphybus","fireantcrypto","all_degens_are_dead",
    "marshallog","Economicrypto","dopaminemaxi","lovejudylee","c0wfarm","mdewstable",
    "Raoni1","theddari_main","pannpunch","waitstudy","airdr0p_lab","crypt0_sea",
    "justicekingsman","tlsrltnf","btc_alt_info","blockmedia","nftimagod","mujammin123",
    "cryptopangpang","dolchanchain","dolbikong","GMBLABS","rolypopa","yobeullyANN",
    "gensencoin","Rowna999","hanabicoin2","killberosDAO","allpointsaremine",
    "cobacknamannounce","doratman18","justdegenguy","lnsanecoin","narockisrock1",
    "MAC_DDDD","dogeland01","web3subin","minebuu_cryptoball","coinsaywhat","Yndegen",
    "joelweb3kr","cryptomacase","JeJeCryptoDiary","gdrcapital","informationdao",
    "MBMweb3","leedogin2","bitethebulletkr","ResearchSena","honey_box_main",
    "chikointhebox","rising_090","coinnesskr","kookookoob","CryptoStreetSignal",
    "minchoisfuture","dolgommagic","yul_papa","c4lvinlocked","murphybus2","pepe_fonji",
    "RezetAquatic","yunlog_announcement","notepad2124","LEEHEESANGDYOR",
    "Sarangbang_Crypto","ewlreads","nojobnoplan","catallactic","cybertruck666",
    "easychartgo","inhu0","Hikicha0_0","taste_suck","money0stack9Notice","homeworkgogo",
    "cryptoquant_kr","Debt50mwon","airdrop_kor","Bananamilkrich","BMTube","forevernft",
    "Jobless_investor","juhyukb","sidejobvip","moneygrid","kimmm1kim","coinboys",
    "BQTelegram","jutrobedzielepsze","inlyeog","jammin0720","namdongX","moon252423",
    "Honeyofwhitesocks_2","Jenti_DeFi","quercus_0","JUSTCRYT","crypt0made","vallettaidea",
    "KOREAalphaDEGEN","shwhwgsicj","coiniseasy","pgyinfo","anancoin","centurywhale",
    "plusevdeal","baborphantkr","Capitalism_Academy","kdp_dao","btcbullforever",
    "havelaw","SnowCrypto1","cubestudy1557","billair1","alpha_duo","popo5M","RezetSide",
    "tangtangbox","nethery2004","FourPillarsFP","Bounty_ATM","soomoktube","xvgwhitedog2",
    "ms0life","myu_moonyu","CoinWiki_MMWW","eastsouthwind","cctgavong","vc_21m",
    "slav_insight","tenaxcrypto","pachepunch","YAPHOPE","dusrmsss","cobak_alert",
    "Roh0517","Board_the_Ark","retrodao","cryptocurrencymage","PASACREW","HeadingtoRome",
    "Ugh_HH","look4treasure","funkyonchain","churin0329","leo_autotrading","cobling",
    "honey_drfox","limelight_kor","kkda8282","karmycrypto","gogangnam40","Titanium_SPOON",
    "stay_news","Katzenote","honeymouse1003","KryptoKlang","Dynastylabs","MingsBog",
    "yeouidobi","CryptoOwlNotice","funkyongamble","investlikejohn","teachmecoins",
    "heedan22","goodvibeai","coinking77777","liambitcoin","c_ryptodiary",
    "yeolchoongNotice","RWAkr","jtakenotice1","DannyCryptoWorld","heunnnnnn","zettgroup",
    "AlanInfoExchange","R_0_D_0_L","JOOONGDO","kwakCrypto","bestyeezus","exilist_official",
    "xangle_research","SOLful_hodl_life","umjuninsight","continuouslearningmatthew",
    "bnbchainkr","shadow_investor_ann","tiger_research","rere2win","jibegagosian",
    "airdropAScenter","testnetduggang","ModuDAO_ANN","claireroom","uksangtrashcan",
    "investmenttech","darkpagu","Jinstori","legoleecm777","mmormm123",
    "korea_crypto_official","jesam84tele","baroBTC","jungculturalfind","bulbul2cryptoDAO",
    "sonnicko","eastgoonercrypto","jason_nest","AllroundResearchanCrypto","kwondoll_2",
    "cblaboratory","katimad","wise_degen_house","eksoo_announce","realKoreanguy",
    "prediction_markets_info","otakurypto","dongmaryeo","honeylab1","sry_father",
    "HHBOX2","blockschool","getmoneywithbrother","FackMeo","goodkolb","coinpharm",
    "coincodekr","Info_Arbitrage","coin369369","bokjisaideashare","imhedacool",
    "jayplaystudy","RT7research","cryptonote_kr","DeSpread","LovelyGaSaRi","tokenview7",
    "sapiensidea","crypto_class_ann","nuttyflavors","vistalabs","mid_curve",
    "cryptonewsaggr","edchart","kbc80","KORypto_Announce",
]


# ── Telegram 수집 ──────────────────────────────────────────────────────────────

def parse_channel_html(channel: str, html: str, cutoff_dt: datetime) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    posts = []

    for wrap in soup.select(".tgme_widget_message_wrap"):
        date_link = wrap.select_one("a.tgme_widget_message_date")
        if not date_link:
            continue

        time_el = date_link.select_one("time")
        if not time_el:
            continue

        dt_str = time_el.get("datetime", "")
        try:
            dt = datetime.fromisoformat(dt_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if dt < cutoff_dt:
                continue
        except Exception:
            continue

        msg_url = date_link.get("href", "")

        # 본문 텍스트
        text_el = wrap.select_one(".tgme_widget_message_text")
        text = text_el.get_text(separator="\n", strip=True) if text_el else ""

        # 이미지
        has_image = False
        image_url = ""
        photo_el = wrap.select_one("a.tgme_widget_message_photo_wrap")
        if photo_el:
            style = photo_el.get("style", "")
            m = re.search(r"background-image:url\('([^']+)'\)", style)
            if m:
                has_image = True
                image_url = m.group(1)

        if text or has_image:
            posts.append({
                "url": msg_url,
                "text": text[:MAX_POST_TEXT],
                "date": dt_str,
                "has_image": has_image,
                "image_url": image_url,
            })

    return {"channel": channel, "has_posts": len(posts) > 0, "posts": posts}


async def fetch_channel(
    session: aiohttp.ClientSession,
    channel: str,
    cutoff_dt: datetime,
    semaphore: asyncio.Semaphore,
) -> dict:
    async with semaphore:
        url = f"https://t.me/s/{channel}"
        headers = {"User-Agent": "Mozilla/5.0 (compatible; TelegramBot/1.0)"}
        try:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                allow_redirects=True,
            ) as resp:
                if resp.status != 200:
                    return {"channel": channel, "has_posts": False, "posts": []}
                html = await resp.text()
                return parse_channel_html(channel, html, cutoff_dt)
        except Exception as e:
            print(f"[WARN] {channel}: {e}", file=sys.stderr)
            return {"channel": channel, "has_posts": False, "posts": []}


async def fetch_all_channels(channels: list, cutoff_dt: datetime) -> list:
    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=100)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_channel(session, ch, cutoff_dt, semaphore) for ch in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    valid = []
    for r in results:
        if isinstance(r, dict):
            valid.append(r)
    return valid


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


# ── 보고서 생성 ────────────────────────────────────────────────────────────────

def build_report(analysis: dict, total_channels: int, today_str: str, lang: str) -> str:
    ki = analysis.get("key_issues", [])
    ri = analysis.get("repeated_issues", [])
    pp = analysis.get("promo_projects", [])
    np_ = analysis.get("notable_posts", [])

    if lang == "ko":
        r  = f"*📡 텔레그램 KOL 모니터링 데일리 브리핑* — {today_str}\n"
        r += f"이 게시물은 최근 24시간동안 텔레그램 국내 탑 *{total_channels}개*의 KOL들의 포스팅을 분석 요약한 보고서입니다.\n"
        r += "주요 이슈와 동향파악 및 KOL을 이용한 프로젝트들의 홍보내용을 검출해서 고객 후보군을 발굴하여 제안영업이나 협업 제안의 기초자료로 사용하기 위해 만들었습니다.\n\n"
        r += "*🔥 오늘의 핵심 이슈*\n"
        for i in ki:
            r += f"• *{i['title']}*  {i['summary_ko']}  출처: {i['source_url']}\n"
        if not ki: r += "• (해당 없음)\n"
        r += "\n*🔁 중복 언급 이슈*\n"
        for i in ri:
            urls = " ".join(i.get("source_urls", []))
            r += f"• *{i['issue_name']}* ({i['channel_count']}개 채널 언급)  {i['explanation']}  키워드: {i['keywords']}  출처: {urls}\n"
        if not ri: r += "• (해당 없음)\n"
        r += "\n*📣 현재 홍보 집중 프로젝트*\n"
        for p in pp:
            r += f"• *{p['project_name']}* — {p['promo_type']} ({p['kol_count']} KOL, CTA: {p['cta_type']})  키워드: {p['keywords']}\n"
        if not pp: r += "• (해당 없음)\n"
        r += "\n*👀 특이 포스팅*\n"
        for p in np_:
            r += f"• {p['description']}  {p['url']}\n"
        if not np_: r += "• (해당 없음)\n"
    else:
        r  = f"*📡 Telegram Daily Brief* — {today_str}\n"
        r += f"This report analyzes posts from the top *{total_channels}* Korean crypto KOLs on Telegram over the last 24 hours.\n"
        r += "Designed to identify key market trends and promotional activities for business development and partnership opportunities.\n\n"
        r += "*🔥 Top Market Topics Today*\n"
        for i in ki:
            r += f"• *{i['title']}*  {i['summary_en']}  Source: {i['source_url']}\n"
        if not ki: r += "• (none)\n"
        r += "\n*🔁 Repeated Cross-KOL Issues*\n"
        for i in ri:
            urls = " ".join(i.get("source_urls", []))
            r += f"• *{i['issue_name']}* ({i['channel_count']} channels)  {i['explanation']}  Keywords: {i['keywords']}  Sources: {urls}\n"
        if not ri: r += "• (none)\n"
        r += "\n*📣 Projects Currently Being Promoted*\n"
        for p in pp:
            r += f"• *{p['project_name']}* — {p['promo_type']} ({p['kol_count']} KOLs, CTA: {p['cta_type']})  Keywords: {p['keywords']}\n"
        if not pp: r += "• (none)\n"
        r += "\n*👀 Notable Posts*\n"
        for p in np_:
            r += f"• {p['description']}  {p['url']}\n"
        if not np_: r += "• (none)\n"

    return r


# ── Slack 발행 ─────────────────────────────────────────────────────────────────

def _webhook_post(webhook_url: str, payload: dict) -> None:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()


def post_to_slack(kor_report: str, eng_report: str, image_url: str | None) -> None:
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]

    # 한국어 보고서
    _webhook_post(webhook_url, {"text": kor_report})

    # 영어 보고서
    _webhook_post(webhook_url, {"text": eng_report})

    # 핵심 이슈 이미지 URL
    if image_url:
        _webhook_post(webhook_url, {"text": f"📸 핵심 이슈 이미지: {image_url}"})


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
        _webhook_post(
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
    parent_ts = post_to_slack(kor_report, eng_report, image_url)

    print(f"완료! ts={parent_ts}")
    print(
        f"요약: 채널 {len(CHANNELS)}개 모니터링 / "
        f"포스팅 있는 채널 {len(channels_with_posts)}개 / "
        f"총 {len(all_posts)}건 / "
        f"핵심 이슈 {len(ki)}개 / "
        f"발행 성공"
    )


if __name__ == "__main__":
    main()
