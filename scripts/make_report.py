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
    topics = sorted(a.get("topic_counts", {}).items(), key=lambda x: -x[1])[:6]
    hooks = sorted(a.get("hook_counts", {}).items(), key=lambda x: -x[1])[:4]
    celebs = [n for n, _ in a.get("celebs", [])[:6]]
    gap = a.get("authority_gap", {})
    n_ph, n_dr = gap.get("약사", 0), gap.get("의사·명의", 0)

    hook_short = {"질문·미완성(?·이유·비결)": "질문형", "숫자리스트(TOP·N가지)": "숫자",
                  "권위(약사·의사·전문가)": "권위", "손실회피·공포(피해야·독·위험)": "손실",
                  "즉효·시간(하루·N분·싹·쫙)": "즉효", "뒤집기(90%·잘못·사실은)": "뒤집기",
                  "금기·처방(절대·이렇게 드세요)": "금기"}

    lines = [
        f"🩺 홈피드 건강판 리포트 ({a['scanned_at']})",
        f"카드 {a['card_count']} (건강 {a.get('health_card_count','?')})",
        "",
        "🔥 뜨는 주제: " + " · ".join(f"{t}{c}" for t, c in topics),
        "🪝 훅: " + " · ".join(f"{hook_short.get(k,k)}{v}" for k, v in hooks),
        "⭐ 셀럽: " + (" · ".join(celebs) if celebs else "없음"),
        f"💊 약사 {n_ph} vs 의사 {n_dr} → " +
        ("약사 자리 비어있음(기회)" if n_ph <= n_dr else "약사 이미 있음"),
        "",
        f"📊 누적 대시보드: {DASH_URL}",
    ]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
