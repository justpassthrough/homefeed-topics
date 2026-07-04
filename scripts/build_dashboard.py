# -*- coding: utf-8 -*-
"""
data/history.json → docs/index.html (GitHub Pages 누적 대시보드).

구성(위→아래):
  1) 지금 뜨는 '구체' 주제 — 카드를 세부 클러스터로 묶어 정리 (광범위한 '다이어트' X)
  2) 약사 공백 — 의사·전문가가 다루는 실제 카드 + 약사 각도가 비어있는 지점 설명
  3) 분석(훅 분포·셀럽·주제 추이) — 아래로
  4) 지난 스캔
외부 라이브러리 없이 self-contained, 라이트/다크 대응.
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import html
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
DOCS = os.path.join(REPO, "docs")


def esc(s):
    return html.escape(str(s))


def bar_rows(items, maxv, color):
    out = []
    for label, v in items:
        w = int(round((v / maxv) * 100)) if maxv else 0
        out.append(
            f'<div class="row"><span class="lbl">{esc(label)}</span>'
            f'<span class="bar"><span class="fill" style="width:{w}%;background:{color}"></span></span>'
            f'<span class="num">{v}</span></div>')
    return "\n".join(out)


HOOK_SHORT = {"질문·미완성(?·이유·비결)": "질문·미완성", "숫자리스트(TOP·N가지)": "숫자 리스트",
              "권위(약사·의사·전문가)": "권위", "손실회피·공포(피해야·독·위험)": "손실회피·공포",
              "즉효·시간(하루·N분·싹·쫙)": "즉효·시간", "뒤집기(90%·잘못·사실은)": "뒤집기",
              "금기·처방(절대·이렇게 드세요)": "금기·처방"}


def category_blocks(categories):
    """구체 주제 클러스터 — 각 카테고리 헤더 + 카드 묶음."""
    if not categories:
        return "<p class='muted'>데이터 없음</p>"
    out = []
    for cat in categories:
        name, cnt, cards = cat["name"], cat["count"], cat["cards"]
        if name == "기타":
            continue
        verdict = cat.get("verdict", "")
        reason = cat.get("reason", "")
        angle = cat.get("angle", "")
        vclass = ("v-yes" if verdict.startswith("✅") else
                  "v-cond" if verdict.startswith("⚠️") else "v-no")
        head = (f'<div class="cathead"><span class="catname">{esc(name)}</span>'
                f'<span class="catcnt">{cnt}</span></div>'
                f'<div class="verdict {vclass}">{esc(verdict)}</div>'
                f'<div class="why">{esc(reason)}</div>')
        angle_html = (f'<div class="anglehint"><b>약사 각도:</b> {esc(angle)}</div>'
                      if angle and angle != "-" else "")
        shown = cards[:5]
        lis = "".join(f"<li>{esc(c)}</li>" for c in shown)
        more = ""
        if len(cards) > 5:
            rest = "".join(f"<li>{esc(c)}</li>" for c in cards[5:])
            more = f"<details><summary>+{len(cards)-5}개 더</summary><ul>{rest}</ul></details>"
        out.append(f'<div class="cat {vclass}b">{head}{angle_html}<ul>{lis}</ul>{more}</div>')
    return "\n".join(out)


def briefs_section(briefs):
    """온디맨드로 만든 브리프 기록 — 복사 가능한 [A] 블록, 최신순."""
    if not briefs:
        return ("<p class='muted'>아직 만든 브리프가 없어요. 클로드 코드에서 "
                "\"○○ 브리프 줘\"라고 하면 여기 쌓입니다.</p>")
    out = []
    for b in reversed(briefs):
        block = (f"주제: {b.get('topic','')}\n"
                 f"뒤집을 상식: {b.get('flip','')}\n"
                 f"실제(DDS 각도): {b.get('fact','')}\n"
                 f"왜 이 주제: {b.get('why','')}\n"
                 f"CTA: {b.get('cta','')}")
        src = f"<div class='bsrc'>근거 카드: {esc(b['source_card'])}</div>" if b.get("source_card") else ""
        open_attr = " open" if b is briefs[-1] else ""
        out.append(
            f"<details class='brief'{open_attr}>"
            f"<summary><b>#{b.get('id','')} {esc(b.get('topic',''))}</b>"
            f"<span class='bmeta'>{esc(b.get('category',''))} · {esc(b.get('created_at',''))}</span></summary>"
            f"{src}<pre class='bblock'>{esc(block)}</pre></details>")
    return "\n".join(out)


def topic_trend_table(scans):
    recent = scans[-8:]
    tot = Counter()
    for s in recent:
        for c in s.get("categories", []):
            tot[c["name"]] += c["count"]
    top = [t for t, _ in tot.most_common(10) if t != "기타"]
    if not top:
        return "<p class='muted'>아직 추이 데이터가 부족합니다(스캔 누적 시 채워집니다).</p>"
    head = "".join(f"<th>{esc(s['date'][5:])}</th>" for s in recent)
    rows = []
    for t in top:
        cells = ""
        for s in recent:
            v = next((c["count"] for c in s.get("categories", []) if c["name"] == t), 0)
            cells += f"<td>{v or ''}</td>"
        rows.append(f"<tr><th class='tname'>{esc(t)}</th>{cells}</tr>")
    return (f"<table class='trend'><thead><tr><th>주제</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def build():
    hist = json.load(open(os.path.join(DATA, "history.json"), encoding="utf-8"))
    scans = hist.get("scans", [])
    if not scans:
        print("스캔 기록 없음"); return
    latest = scans[-1]
    try:
        briefs = json.load(open(os.path.join(DATA, "briefs.json"), encoding="utf-8")).get("briefs", [])
    except Exception:
        briefs = []

    categories = latest.get("categories", [])
    hooks = sorted(latest.get("hook_counts", {}).items(), key=lambda x: -x[1])
    celebs = latest.get("celebs", [])[:12]
    gap = latest.get("authority_gap", {})
    n_ph = gap.get("약사", 0); n_dr = gap.get("의사·명의", 0)
    doctor_cards = latest.get("doctor_cards", [])

    hmax = max((v for _, v in hooks), default=1)
    cat_html = category_blocks(categories)
    briefs_html = briefs_section(briefs)
    hook_html = bar_rows([(HOOK_SHORT.get(k, k), v) for k, v in hooks], hmax, "var(--c2)")
    celeb_html = " ".join(
        f'<span class="chip">{esc(n)}<i>{c}</i></span>' for n, c in celebs) or "<span class='muted'>없음</span>"
    trend_html = topic_trend_table(scans)
    doc_html = ("".join(f"<li>{esc(c)}</li>" for c in doctor_cards)
                or "<li class='muted'>이번 스캔엔 의사·전문가 카드가 적었습니다.</li>")

    past = "".join(
        f"<li><b>{esc(s['scanned_at'])}</b> · 건강 {s['health_card_count']} · "
        f"{', '.join(c['name'] for c in s.get('categories', [])[:4])}</li>"
        for s in reversed(scans[-15:]))

    doc = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>홈피드 건강판 트렌드</title>
<style>
:root{{--bg:#fafafa;--card:#fff;--tx:#1a1a1a;--mut:#777;--line:#eaeaea;
 --c1:#3b82f6;--c2:#8b5cf6;--c3:#f59e0b;--accent:#ef4444;--chip:#f1f3f6;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1115;--card:#181b21;--tx:#e8e8e8;
 --mut:#8b93a1;--line:#262b34;--chip:#242a33;}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);
 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic',sans-serif;
 line-height:1.5;padding:16px}}
.wrap{{max-width:880px;margin:0 auto}}
h1{{font-size:20px;margin:8px 0 2px}}
.sub{{color:var(--mut);font-size:13px;margin-bottom:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;
 padding:16px 18px;margin-bottom:14px}}
.card>h2{{font-size:15px;margin:0 0 4px}}
.card .hint{{color:var(--mut);font-size:12px;margin:0 0 12px}}
.catgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:12px}}
.cat{{border:1px solid var(--line);border-radius:11px;padding:11px 13px;background:var(--bg)}}
.cathead{{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}}
.catname{{font-weight:700;font-size:13.5px}}
.catcnt{{background:var(--c1);color:#fff;border-radius:20px;font-size:11px;
 padding:1px 9px;font-weight:700}}
.verdict{{font-size:12px;font-weight:700;margin-bottom:2px}}
.v-yes{{color:#16a34a}} .v-cond{{color:#d97706}} .v-no{{color:var(--mut)}}
.cat.v-yesb{{border-color:#16a34a55}} .cat.v-condb{{border-color:#d9770655}}
.why{{font-size:11.5px;color:var(--mut);margin-bottom:7px;line-height:1.4}}
.anglehint{{font-size:11.5px;background:var(--chip);border-radius:7px;
 padding:5px 8px;margin-bottom:7px}}
.anglehint b{{color:var(--c2)}}
.cat ul{{margin:0;padding-left:16px;font-size:12.5px}}
.cat li{{margin:3px 0}}
.cat details{{margin-top:5px}} .cat summary{{cursor:pointer;color:var(--mut);font-size:12px}}
.row{{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}}
.lbl{{width:110px;flex:none;white-space:nowrap}}
.bar{{flex:1;background:var(--line);border-radius:6px;height:12px;overflow:hidden}}
.fill{{display:block;height:100%;border-radius:6px}}
.num{{width:26px;text-align:right;color:var(--mut);flex:none}}
.chip{{display:inline-block;background:var(--chip);border-radius:20px;
 padding:4px 11px;margin:3px;font-size:13px}}
.chip i{{color:var(--mut);font-style:normal;margin-left:5px;font-size:11px}}
.gapbox{{background:var(--bg);border:1px dashed var(--accent);border-radius:11px;
 padding:11px 13px;margin:10px 0;font-size:13px}}
.gapbox b{{color:var(--accent)}}
.angle{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
.angle span{{background:var(--chip);border-radius:6px;padding:3px 9px;font-size:12px}}
ul.docs{{margin:8px 0 0;padding-left:18px;font-size:12.5px}}
ul.docs li{{margin:3px 0}}
table.trend{{width:100%;border-collapse:collapse;font-size:12px}}
table.trend th,table.trend td{{border:1px solid var(--line);padding:4px 6px;text-align:center}}
table.trend th.tname{{text-align:left;white-space:nowrap}}
.muted{{color:var(--mut);font-size:12.5px}}
details.brief{{border:1px solid var(--line);border-radius:10px;padding:9px 12px;margin:8px 0;background:var(--bg)}}
details.brief[open]{{border-color:var(--c1)}}
details.brief summary{{cursor:pointer;font-size:13.5px;display:flex;
 justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}}
.bmeta{{color:var(--mut);font-size:11px;font-weight:400}}
.bsrc{{color:var(--mut);font-size:11.5px;margin:8px 0 4px}}
.bblock{{background:var(--card);border:1px solid var(--line);border-radius:8px;
 padding:11px 13px;font-size:12.5px;line-height:1.6;white-space:pre-wrap;
 word-break:break-word;font-family:'Malgun Gothic',sans-serif;margin:6px 0 0}}
details.blk summary{{cursor:pointer;color:var(--mut);font-size:13px}}
.foot{{color:var(--mut);font-size:11px;text-align:center;margin:18px 0}}
</style></head><body><div class="wrap">
<h1>🩺 홈피드 건강판 트렌드</h1>
<div class="sub">네이버 모바일 홈피드 '건강판' 3일마다 스캔 · 최근 <b>{esc(latest['scanned_at'])}</b>
 · 카드 {latest['card_count']}(건강 {latest['health_card_count']})</div>

<div class="card"><h2>🔥 지금 뜨는 주제 (약사+DDS 적합도순)</h2>
<p class="hint">피드 카드를 세부 주제로 묶고, <b>내 블로그에 먹히는지 자동 판정</b>(✅추천/⚠️조건부/❌패스).
 크기가 아니라 '약사·DDS가 차별화되는가'로 정렬 · 숫자는 카드 수</p>
<div class="catgrid">{cat_html}</div></div>

<div class="card"><h2>📋 만든 글감 브리프 ({len(briefs)})</h2>
<p class="hint">클로드 코드에서 요청해 만든 브리프 기록 · 최신순 · 블록 복사해서 글쓰기 프로젝트에 붙여넣기</p>
{briefs_html}</div>

<div class="card"><h2>💊 약사가 파고들 빈자리</h2>
<p class="hint">아래 주제들은 지금 <b>의사·전문가 목소리</b>로 설명되는 중 —
 약사 관점은 비어 있어요(이번 스캔: 약사 {n_ph} vs 의사·전문가 {n_dr}).</p>
<div class="gapbox">같은 주제라도 <b>약사가 잡으면 차별화</b>되는 각도:
<div class="angle"><span>복용 타이밍·순서</span><span>약물 상호작용</span>
<span>영양제↔처방약 병용</span><span>성분 실효성·용량</span><span>부작용 대처</span></div></div>
<p class="hint" style="margin-top:10px">지금 의사·전문가가 다루고 있는 실제 카드:</p>
<ul class="docs">{doc_html}</ul></div>

<details class="blk"><summary>📊 상세 분석 (훅 패턴 · 셀럽 · 주제 추이) 펼치기</summary>
<div class="card" style="margin-top:12px"><h2>🪝 훅 패턴 분포</h2>{hook_html}</div>
<div class="card"><h2>⭐ 감지된 셀럽</h2>{celeb_html}</div>
<div class="card"><h2>📈 주제 추이 (최근 스캔)</h2>{trend_html}</div>
</details>

<div class="card"><h2>🗂 지난 스캔</h2>
<details class="blk"><summary>기록 {len(scans)}회 펼치기</summary><ul>{past}</ul></details></div>

<div class="foot">자동 생성 · homefeed-topics · 데이터: 네이버 모바일 홈피드(로컬 스캔)</div>
</div></body></html>"""

    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"대시보드 생성 → docs/index.html ({len(scans)}회 스캔, 카테고리 {len(categories)}개)")


if __name__ == "__main__":
    build()
