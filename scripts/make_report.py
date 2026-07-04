# -*- coding: utf-8 -*-
"""
data/latest_analysis.json → 텔레그램용 요약 텍스트(stdout).
run_homefeed_local.ps1이 이 출력을 notify로 보낸다.
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
DASH_URL = "https://justpassthrough.github.io/homefeed-topics/"


def main():
    a = json.load(open(os.path.join(DATA, "latest_analysis.json"), encoding="utf-8"))
    cats = [c for c in a.get("categories", []) if c["name"] != "기타"][:6]
    celebs = [n for n, _ in a.get("celebs", [])[:6]]
    gap = a.get("authority_gap", {})
    n_ph, n_dr = gap.get("약사", 0), gap.get("의사·명의", 0)

    lines = [
        f"🩺 홈피드 건강판 리포트 ({a['scanned_at']})",
        f"카드 {a['card_count']} (건강 {a.get('health_card_count','?')})",
        "",
        "🔥 지금 뜨는 주제:",
    ]
    for c in cats:
        sample = c["cards"][0] if c.get("cards") else ""
        sample = (sample[:24] + "…") if len(sample) > 25 else sample
        lines.append(f"  • {c['name']} ({c['count']}) — {sample}")
    lines += [
        "",
        "⭐ 셀럽: " + (" · ".join(celebs) if celebs else "없음"),
        f"💊 약사 {n_ph} vs 의사·전문가 {n_dr} → " +
        ("약사 관점 빈자리(차별화 기회)" if n_ph <= n_dr else "약사 콘텐츠 이미 있음"),
        "",
        f"📊 주제별 정리·의사공백 상세: {DASH_URL}",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
