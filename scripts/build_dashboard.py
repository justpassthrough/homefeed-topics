# -*- coding: utf-8 -*-
"""
data/history.json → docs/index.html (GitHub Pages 누적 대시보드).

스캔이 쌓일수록 '홈피드 건강판에 뜨는 주제/훅/셀럽'의 흐름이 보인다.
외부 라이브러리 없이 self-contained (GitHub Pages 정적 서빙), 라이트/다크 대응.
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


def topic_trend_table(scans):
    """주제별 스캔 간 추이 (최근 8회)."""
    recent = scans[-8:]
    all_topics = Counter()
    for s in recent:
        for t, c in s.get("topic_counts", {}).items():
            all_topics[t] += c
    top = [t for t, _ in all_topics.most_common(12)]
    if not top:
        return "<p class='muted'>아직 데이터가 부족합니다.</p>"
    head = "".join(f"<th>{esc(s['date'][5:])}</th>" for s in recent)
    rows = []
    for t in top:
        cells = "".join(
            f"<td>{s.get('topic_counts', {}).get(t, 0) or ''}</td>" for s in recent)
        rows.append(f"<tr><th class='tname'>{esc(t)}</th>{cells}</tr>")
    return (f"<table class='trend'><thead><tr><th>주제</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>")


def build():
    hist = json.load(open(os.path.join(DATA, "history.json"), encoding="utf-8"))
    scans = hist.get("scans", [])
    if not scans:
        print("스캔 기록 없음"); return
    latest = scans[-1]

    topics = sorted(latest.get("topic_counts", {}).items(), key=lambda x: -x[1])[:12]
    hooks = sorted(latest.get("hook_counts", {}).items(), key=lambda x: -x[1])
    celebs = latest.get("celebs", [])[:12]
    gap = latest.get("authority_gap", {})
    n_ph = gap.get("약사", 0); n_dr = gap.get("의사·명의", 0)
    cards = latest.get("health_cards", [])

    tmax = max((v for _, v in topics), default=1)
    hmax = max((v for _, v in hooks), default=1)

    topic_html = bar_rows(topics, tmax, "var(--c1)")
    hook_html = bar_rows(hooks, hmax, "var(--c2)")
    celeb_html = " ".join(
        f'<span class="chip">{esc(n)}<i>{c}</i></span>' for n, c in celebs) or "<span class='muted'>감지된 셀럽 없음</span>"
    cards_html = "\n".join(f"<li>{esc(c)}</li>" for c in cards)
    trend_html = topic_trend_table(scans)

    past = "".join(
        f"<li><b>{esc(s['scanned_at'])}</b> · 건강카드 {s['health_card_count']} · "
        f"주제 {', '.join(list(s.get('topic_counts', {}).keys())[:5])}</li>"
        for s in reversed(scans[-15:]))

    gap_msg = ("약사 목소리가 비어있음 — 차별화 기회" if n_ph <= n_dr
               else "약사 콘텐츠 이미 존재")

    doc = f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>홈피드 건강판 트렌드</title>
<style>
:root{{--bg:#fafafa;--card:#fff;--tx:#1a1a1a;--mut:#777;--line:#eaeaea;
 --c1:#3b82f6;--c2:#8b5cf6;--c3:#f59e0b;--accent:#ef4444;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0f1115;--card:#181b21;--tx:#e8e8e8;
 --mut:#8b93a1;--line:#262b34;}}}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--tx);
 font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic',sans-serif;
 line-height:1.5;padding:16px}}
.wrap{{max-width:860px;margin:0 auto}}
h1{{font-size:20px;margin:8px 0 2px}}
.sub{{color:var(--mut);font-size:13px;margin-bottom:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;
 padding:16px 18px;margin-bottom:14px}}
.card h2{{font-size:15px;margin:0 0 12px;display:flex;align-items:center;gap:6px}}
.row{{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}}
.lbl{{width:150px;flex:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bar{{flex:1;background:var(--line);border-radius:6px;height:12px;overflow:hidden}}
.fill{{display:block;height:100%;border-radius:6px}}
.num{{width:26px;text-align:right;color:var(--mut);flex:none}}
.chip{{display:inline-block;background:var(--line);border-radius:20px;
 padding:4px 11px;margin:3px;font-size:13px}}
.chip i{{color:var(--mut);font-style:normal;margin-left:5px;font-size:11px}}
.gap{{font-size:14px}}
.gap b{{color:var(--accent)}}
ul.cards{{margin:0;padding-left:18px;font-size:13px;columns:1}}
ul.cards li{{margin:3px 0}}
table.trend{{width:100%;border-collapse:collapse;font-size:12px}}
table.trend th,table.trend td{{border:1px solid var(--line);padding:4px 6px;text-align:center}}
table.trend th.tname{{text-align:left;white-space:nowrap}}
.muted{{color:var(--mut);font-size:13px}}
details{{font-size:13px}} summary{{cursor:pointer;color:var(--mut)}}
.foot{{color:var(--mut);font-size:11px;text-align:center;margin:18px 0}}
</style></head><body><div class="wrap">
<h1>🩺 홈피드 건강판 트렌드</h1>
<div class="sub">네이버 모바일 홈피드 '건강판'을 3일마다 스캔 · 최근 스캔 <b>{esc(latest['scanned_at'])}</b>
 · 카드 {latest['card_count']}개(건강 {latest['health_card_count']})</div>

<div class="card"><h2>🔥 지금 뜨는 주제</h2>{topic_html}</div>

<div class="card"><h2>🪝 훅 패턴 분포</h2>{hook_html}</div>

<div class="card"><h2>⭐ 감지된 셀럽 (건강 앵글)</h2>{celeb_html}</div>

<div class="card"><h2>💊 권위 공백</h2>
<div class="gap">약사 <b>{n_ph}건</b> vs 의사·명의 {n_dr}건 → {esc(gap_msg)}</div></div>

<div class="card"><h2>📈 주제 추이 (최근 스캔)</h2>{trend_html}</div>

<div class="card"><h2>📰 이번 피드 카드 ({len(cards)})</h2>
<ul class="cards">{cards_html}</ul></div>

<div class="card"><h2>🗂 지난 스캔</h2>
<details><summary>기록 {len(scans)}회 펼치기</summary><ul>{past}</ul></details></div>

<div class="foot">자동 생성 · homefeed-topics · 데이터 출처: 네이버 모바일 홈피드(로컬 스캔)</div>
</div></body></html>"""

    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"대시보드 생성 → docs/index.html ({len(scans)}회 스캔 반영)")


if __name__ == "__main__":
    build()
