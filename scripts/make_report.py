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
    cats = [c for c in a.get("categories", []) if c["name"] != "기타"]
    rec = [c for c in cats if c.get("verdict", "").startswith("✅")]
    cond = [c for c in cats if c.get("verdict", "").startswith("⚠️")]
    celebs = [n for n, _ in a.get("celebs", [])[:6]]

    lines = [
        f"🩺 홈피드 건강판 리포트 ({a['scanned_at']})",
        f"카드 {a['card_count']} (건강 {a.get('health_card_count','?')})",
        "",
        "✅ 오늘 밀 만한 주제 (약사+DDS 적합):",
    ]
    if rec:
        for c in rec:
            sample = c["cards"][0] if c.get("cards") else ""
            sample = (sample[:22] + "…") if len(sample) > 23 else sample
            lines.append(f"  • {c['name']} ({c['count']})")
            lines.append(f"     └ {sample}")
            lines.append(f"     └ 각도: {c.get('angle','')}")
    else:
        lines.append("  (이번 스캔엔 ✅추천 주제가 적음)")
    if cond:
        lines.append("")
        lines.append("⚠️ 조건부(엮으면 됨): " + " · ".join(f"{c['name']}({c['count']})" for c in cond[:5]))
    lines += [
        "",
        "⭐ 셀럽: " + (" · ".join(celebs) if celebs else "없음"),
        "",
        f"📊 판정·각도·의사공백 상세: {DASH_URL}",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
