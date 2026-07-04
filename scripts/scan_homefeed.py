# -*- coding: utf-8 -*-
"""
홈피드 스캐너 (독립 프로젝트, 키워드 딥다이브와 무관).

핵심 아이디어: 검색 키워드를 조합하는 게 아니라, **네이버 홈피드 '건강판'에 지금
실제로 떠 있는 카드**를 통째로 읽어와서, 어떤 훅/주제/셀럽이 스크롤을 멈추게 하는지
역산한다. (사람이 스크린샷 보고 하던 '첫 분석'을 자동화)

동작:
  1) 로컬 Playwright(헤드리스)로 m.naver.com → '건강' 판 클릭 → 스크롤하며 카드 제목 수집
     (네이버는 Claude 내장 도구엔 차단이지만, 내 PC의 로컬 브라우저는 정상 접근)
  2) 제목 정제(페이지네이션/재생시간 등 노이즈 제거)
  3) 자동 분석: 훅 패턴 분류 · 셀럽 추출 · 주제 빈도 · '약사 vs 의사' 공백
  4) data/feed_snapshot.json(원본) + data/latest_analysis.json(분석) 저장 + 리포트 출력

이 스크립트는 '분석 리포트'까지만 만든다(무료·API 0). 완성된 글감 제목/썸네일은
Claude가 이 리포트를 읽어 온디맨드로 다듬는다(nature-daily의 스크래핑↔생성 분리).
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import json
import os
import re
from collections import Counter
from datetime import datetime, timezone, timedelta

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
KST = timezone(timedelta(hours=9))

MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
             "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
             "Mobile/15E148 Safari/604.1")

# ── 제목 정제 ──────────────────────────────────────────────
_PAGERUN = re.compile(r"^(?:\d+페이지)+")
_RANK = re.compile(r"^\d+위\s*")
_PLAYTIME = re.compile(r"^재생시간\s*\d{1,2}:\d{2}\s*")
_JUNK = {"판 관리 바로가기", "네이버 Na", "통합MY", "앱 사용하기"}

def clean_title(t):
    t = " ".join(t.split())
    t = _PLAYTIME.sub("", t)
    t = _PAGERUN.sub("", t)
    t = _RANK.sub("", t)
    return t.strip()

# ── 훅 패턴 분류 (홈피드 첫 분석에서 도출한 7종) ──────────────
HOOK_RULES = [
    ("뒤집기(90%·잘못·사실은)", re.compile(r"90%|잘못|사실은|알고보|인 줄|의외|숨은|몰랐")),
    ("숫자리스트(TOP·N가지)", re.compile(r"TOP\s?\d|\d\s?가지|\d\s?개|딱\s?\d|\d위")),
    ("손실회피·공포(피해야·독·위험)", re.compile(r"피해야|피하라|피하세요|안 하면|놓치|독|위험|망치|늙|혹사|찐다|손해")),
    ("권위(약사·의사·전문가)", re.compile(r"약사|의사|전문가|명의|박사|교수|한의사|영양사")),
    ("즉효·시간(하루·N분·싹·쫙)", re.compile(r"하루|\d\s?분|\d\s?주|\d\s?일 만|싹|쫙|쏙|당장|즉시|바로")),
    ("금기·처방(절대·이렇게 드세요)", re.compile(r"절대|이렇게 (드|하)세요|만 (지키|하)세요|먹지 ?마|끊으면")),
    ("질문·미완성(?·이유·비결)", re.compile(r"\?|이유|비결|정체|진실|왜|이것|이 (과일|음식|채소|동작|운동)")),
]

# ── 주제 사전 (오탐 줄이려 되도록 2자+ 특정어. 간→간식/시간, 장→장윤정 오탐 회피) ──
TOPIC_WORDS = ["혈당", "당뇨", "뱃살", "복부", "다이어트", "영양제", "위고비", "마운자로",
               "비만", "채소", "과일", "커피", "치매", "면역력", "간질환", "간기능", "간 건강",
               "간건강", "콜라겐", "유산균", "단백질", "탈모", "관절", "고관절", "허리",
               "붓기", "독소", "감량", "식단", "혈압", "콜레스테롤", "수면", "피부",
               "갱년기", "폐경", "스트레칭", "통증", "팔뚝살", "허벅지", "마그네슘",
               "밀크씨슬", "칼로리", "체중", "폭식", "공복"]
# 화면 표시용으로 여러 표기를 한 주제로 합침
TOPIC_MERGE = {"간질환": "간건강", "간기능": "간건강", "간 건강": "간건강"}

# 셀럽 후보(정확 사전 없이도 '이름+건강앵글' 패턴으로 잡되, 오탐 줄이려 앵글어 요구)
CELEB_ANGLE = re.compile(r"(감량|다이어트|식단|마른|살 뺀|비결|근황|얼굴|몸매|건강)")
NAME_RE = re.compile(r"([가-힣]{2,4})(?:씨|님)?\s*(?:의|,|은|는|이|가)?\s")

# ── 구체 주제 분류 (광범위한 '다이어트' 대신 세부 클러스터) ──────────
# 위에서부터 먼저 매칭. 셀럽 감량은 별도 처리(이름+앵글 필요).
CATEGORY_RULES = [
    ("비만약(위고비·마운자로)", re.compile(r"위고비|마운자로|삭센다|비만약|GLP|먹는 살|천연 위고비|일라이릴리")),
    ("혈당·당뇨", re.compile(r"혈당|당뇨|공복|인슐린|췌장|혈당스파이크")),
    ("간 건강", re.compile(r"간질환|간기능|간건강|간 건강|간에|ALT|지방간|간이|쿠퍼스")),
    ("콜레스테롤·혈압·혈관", re.compile(r"콜레스테롤|고지혈|고혈압|혈압|혈관|중성지방")),
    ("뒤집기 음식·식습관", re.compile(r"90%|잘못 먹|이렇게 (드|먹)|먹는 시간|폭식|공복에|아침 (공복|에)|먹었더니|채소|당 떨어|먹지 ?마")),
    ("운동·통증·스트레칭", re.compile(r"운동|스트레칭|통증|허리|고관절|관절|허벅지|팔뚝|뱃살|복근|코어|데드리프트|자세|체형|하체|근력")),
    ("탈모·모발", re.compile(r"탈모|모발|샴푸|머리숱|휑|정수리")),
    ("피부·노화", re.compile(r"피부|주름|탄력|리프팅|턱선|미백|기미|잡티")),
    ("갱년기·폐경·호르몬", re.compile(r"갱년기|폐경|호르몬|여성 건강")),
    ("면역·피로", re.compile(r"면역|피로|기력|영양 부족")),
    ("치매·뇌 건강", re.compile(r"치매|뇌|기억력|인지|정서")),
    ("영양제·성분", re.compile(r"영양제|비타민|유산균|프로바이오틱스|콜라겐|마그네슘|오메가|밀크씨슬|루테인|아연|셀레늄")),
]
AUTHORITY_RE = re.compile(r"약사|의사|명의|전문가|박사|교수|한의사|영양사")
DOCTOR_RE = re.compile(r"의사|명의|전문가|박사|교수|한의사")
# 크리에이터 프로필·UI 노이즈 (카드가 아님)
NOISE_RE = re.compile(r"구독자|팔로워|이웃|재생시간|입력 내용|도움말|바로가기|자동완성|"
                      r"검색 이력|설정|더 알아보기|지금 신청|앱 사용|판 관리")
# 건강 카드 판별용 키워드
HEALTH_KW = TOPIC_WORDS + ["약사", "의사", "명의", "운동", "몸매", "혈", "다이어트",
                           "감량", "면역", "당뇨", "암", "폐경", "살 빼", "살뺀", "식단",
                           "스트레칭", "통증", "붓기", "독소", "근육", "호르몬", "숙면"]

def is_health_card(c):
    return any(k in c for k in HEALTH_KW) and not NOISE_RE.search(c)


def categorize(cards, celeb_names):
    """각 카드를 구체 주제 클러스터에 배정. 셀럽 감량은 최우선."""
    buckets = {}
    def put(cat, card):
        buckets.setdefault(cat, []).append(card)
    for c in cards:
        # 셀럽 감량·식단: 감지된 셀럽 이름 + 감량/식단 앵글
        if any(n in c for n in celeb_names) and re.search(r"감량|식단|kg|마른|살 뺀|살 뺐|비결|몸매|다이어트", c):
            put("셀럽 감량·식단", c); continue
        matched = False
        for cat, rx in CATEGORY_RULES:
            if rx.search(c):
                put(cat, c); matched = True; break
        if not matched:
            put("기타", c)
    return buckets


def extract_celebs(titles):
    """제목에서 '유명인 + 건강앵글' 조합 추출. 오탐 억제 위해 앵글어 동반 필수."""
    try:
        from kiwipiepy import Kiwi
        kiwi = Kiwi()
        use_kiwi = True
    except Exception:
        use_kiwi = False
    found = Counter()
    for t in titles:
        if not CELEB_ANGLE.search(t):
            continue
        names = set()
        if use_kiwi:
            for tok in kiwi.tokenize(t):
                if tok.tag == "NNP" and 2 <= len(tok.form) <= 4 and re.fullmatch(r"[가-힣]+", tok.form):
                    names.add(tok.form)
        # 따옴표 안 이름도 보조 추출
        for m in re.finditer(r"[\"“]?([가-힣]{2,4})[\"”]?", t[:12]):
            pass
        for n in names:
            found[n] += 1
    # 흔한 일반명사 오탐 제거
    STOP = {"다이어트", "영양제", "건강", "운동", "식단", "감량", "비결", "근황", "채소", "과일",
            "한국", "여름", "겨울", "우리", "요즘", "진짜", "이것", "그것", "무엇", "바른",
            "데드", "나비", "요가", "코어", "스쿼트", "레시피", "습관", "루틴", "마사지",
            "체형", "자세", "리프팅", "레이저", "피부과", "이습관", "특징",
            # 장소·역할·태그 오탐
            "워킹맘", "헬시타임", "뉴욕", "서울", "강남", "미국", "일본", "한국인", "직장인",
            "주부", "엄마", "아빠", "남편", "아내", "아들", "언니", "그녀", "남자", "여자",
            "당뇨", "혈당", "면역", "폐경", "갱년기", "복부", "뱃살", "허벅지", "관절"}
    # 장소/역할 접미사로 끝나면 인명 아님 (…맘/…타임/…맨/…족/…러/…님)
    def bad(n):
        return n in STOP or n[-1] in {"맘", "맨", "족", "님"} or n.endswith("타임")
    return [(n, c) for n, c in found.most_common(25) if not bad(n)]


def scrape_health_panel(max_scroll=8):
    cards = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(user_agent=MOBILE_UA, viewport={"width": 390, "height": 844},
                            locale="ko-KR")
        pg = ctx.new_page()
        pg.goto("https://m.naver.com/", wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(2000)
        # '건강' 판 클릭 (SPA 라우트)
        clicked = False
        try:
            pg.get_by_role("link", name="건강", exact=True).first.click(timeout=8000)
            clicked = True
        except Exception:
            try:
                pg.eval_on_selector_all("a", """els=>{for(const e of els){
                    if((e.innerText||'').trim()==='건강'){e.click();return true;}}return false;}""")
                clicked = True
            except Exception:
                pass
        pg.wait_for_timeout(3500)
        for _ in range(max_scroll):
            pg.mouse.wheel(0, 3000)
            pg.wait_for_timeout(1100)
        raw = pg.eval_on_selector_all(
            "strong, a, span",
            "els=>els.map(e=>(e.innerText||'').trim()).filter(t=>t.length>=8 && t.length<=60)")
        b.close()
    seen = set()
    for t in raw:
        c = clean_title(t)
        if len(c) < 8 or c in _JUNK or c in seen:
            continue
        seen.add(c)
        cards.append(c)
    return cards, clicked


def analyze(cards):
    """cards = 건강 카드 서브셋(노이즈 제거됨)에 대한 분석."""
    # 훅 분류
    hook_hits = {name: [] for name, _ in HOOK_RULES}
    for t in cards:
        for name, rx in HOOK_RULES:
            if rx.search(t):
                hook_hits[name].append(t)
    hook_counts = {k: len(v) for k, v in hook_hits.items()}
    # 주제 빈도 (표기 통합)
    topic_counts = Counter()
    for t in cards:
        matched = set()
        for w in TOPIC_WORDS:
            if w in t:
                matched.add(TOPIC_MERGE.get(w, w))
        for w in matched:
            topic_counts[w] += 1
    # 셀럽
    celebs = extract_celebs(cards)
    celeb_names = [n for n, _ in celebs]
    # 구체 주제 클러스터
    buckets = categorize(cards, celeb_names)
    # 카테고리 정렬(카드 많은 순), 각 대표 카드 3개
    categories = []
    for cat, cs in sorted(buckets.items(), key=lambda x: -len(x[1])):
        if cat == "기타":
            continue
        categories.append({"name": cat, "count": len(cs), "cards": cs})
    if "기타" in buckets:
        categories.append({"name": "기타", "count": len(buckets["기타"]), "cards": buckets["기타"]})
    # 약사 vs 의사 공백 + 의사류가 다룬 실제 카드(공백 설명용)
    n_pharm = sum(1 for t in cards if "약사" in t)
    doctor_cards = [t for t in cards if DOCTOR_RE.search(t) and "약사" not in t]
    n_doc = len(doctor_cards)
    return {
        "hook_counts": dict(sorted(hook_counts.items(), key=lambda x: -x[1])),
        "hook_examples": {k: v[:4] for k, v in hook_hits.items()},
        "topic_counts": dict(topic_counts.most_common(20)),
        "categories": categories,
        "celebs": celebs,
        "authority_gap": {"약사": n_pharm, "의사·명의": n_doc},
        "doctor_cards": doctor_cards[:12],
    }


def main():
    now = datetime.now(KST)
    print(f"[{now:%Y-%m-%d %H:%M}] 건강판 스캔 시작…")
    cards, clicked = scrape_health_panel()
    print(f"  건강 탭 클릭={clicked} · 수집 카드 {len(cards)}개")
    if len(cards) < 15:
        print("  ⚠️ 카드가 너무 적음 — 네이버 구조 변경 or 로딩 실패 가능")
    # 건강 카드만 추림(노이즈·크리에이터 프로필 제거) → 이 서브셋으로 분석
    health_cards = [c for c in cards if is_health_card(c)]
    print(f"  건강 카드 {len(health_cards)}개 (전체 {len(cards)})")
    a = analyze(health_cards)

    os.makedirs(DATA, exist_ok=True)
    stamp = now.strftime("%Y-%m-%d %H:%M")
    snap = {"scanned_at": stamp, "panel": "건강",
            "card_count": len(cards), "cards": cards}
    json.dump(snap, open(os.path.join(DATA, "feed_snapshot.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    analysis = {"scanned_at": stamp, "card_count": len(cards),
                "health_card_count": len(health_cards),
                "health_cards": health_cards, **a}
    json.dump(analysis, open(os.path.join(DATA, "latest_analysis.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    # 누적 히스토리 append (같은 날 중복 스캔은 덮어씀)
    hist_path = os.path.join(DATA, "history.json")
    try:
        hist = json.load(open(hist_path, encoding="utf-8"))
    except Exception:
        hist = {"scans": []}
    rec = {"scanned_at": stamp, "date": now.strftime("%Y-%m-%d"),
           "card_count": len(cards), "health_card_count": len(health_cards),
           "hook_counts": a["hook_counts"], "topic_counts": a["topic_counts"],
           "categories": a["categories"], "celebs": a["celebs"],
           "authority_gap": a["authority_gap"], "doctor_cards": a["doctor_cards"],
           "health_cards": health_cards}
    hist["scans"] = [s for s in hist.get("scans", []) if s.get("date") != rec["date"]]
    hist["scans"].append(rec)
    hist["scans"].sort(key=lambda s: s["scanned_at"])
    json.dump(hist, open(hist_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"  누적 히스토리: {len(hist['scans'])}회 스캔 기록")

    # 리포트 출력
    print("\n" + "=" * 52)
    print(f"  홈피드 건강판 자동 분석 · {snap['scanned_at']} · 카드 {len(cards)}개")
    print("=" * 52)
    print("\n[훅 패턴 분포]")
    for k, v in a["hook_counts"].items():
        print(f"  {v:2d}  {k}")
    print("\n[뜨는 주제 TOP]")
    for w, c in list(a["topic_counts"].items())[:12]:
        print(f"  {c:2d}  {w}")
    print("\n[감지된 셀럽(건강앵글 동반)]")
    for n, c in a["celebs"][:10]:
        print(f"  {c:2d}회  {n}")
    print(f"\n[권위 공백]  약사 {a['authority_gap']['약사']}건  vs  의사·명의 {a['authority_gap']['의사·명의']}건"
          f"  → 약사 목소리 {'비어있음(차별화 기회)' if a['authority_gap']['약사'] <= a['authority_gap']['의사·명의'] else '이미 있음'}")
    print(f"\n저장 → data/feed_snapshot.json · data/latest_analysis.json")


if __name__ == "__main__":
    main()
