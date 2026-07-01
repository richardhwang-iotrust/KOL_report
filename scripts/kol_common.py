#!/usr/bin/env python3
"""
공용 모듈: KOL 채널 목록, 텔레그램 수집 로직, Slack 리포트 생성.

- API 키가 필요 없는 순수 수집/포맷 로직만 담습니다.
- 분석(Claude 호출)은 실행 방식에 따라 달라집니다:
    * telegram_brief.py  → Anthropic API 직접 호출 (종량제 크레딧 필요)
    * fetch_posts.py + publish.py → Claude Code 루틴 에이전트가 분석 (구독 사용)
"""

import asyncio
import re
import sys
from datetime import datetime, timedelta, timezone

import aiohttp
from bs4 import BeautifulSoup

# ── 설정 ───────────────────────────────────────────────────────────────────────
KST = timezone(timedelta(hours=9))
SLACK_CHANNEL = "C0B5H4AAN02"
CONCURRENCY = 25          # 동시 요청 수
REQUEST_TIMEOUT = 30      # 채널당 타임아웃(초)
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


# ── 텔레그램 수집 ──────────────────────────────────────────────────────────────

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

def webhook_post(webhook_url: str, payload: dict) -> None:
    import json
    import urllib.request
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        resp.read()
