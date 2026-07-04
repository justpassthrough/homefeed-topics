# -*- coding: utf-8 -*-
"""
온디맨드로 만든 '글감 브리프'를 data/briefs.json에 누적 저장.
(터미널 일회성으로 날리지 않고 대시보드에 계속 쌓아 다시 꺼내보게)

사용: Claude가 브리프 JSON 파일을 만들어 경로로 넘김
  python scripts/save_brief.py <brief.json>

brief.json 필드(한글 그대로):
  topic(주제), category(주제군), flip(뒤집을 상식), fact(실제·DDS 각도),
  why(왜 이 주제), cta(CTA), source_card(근거 카드, 선택)
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
import json
import os
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
KST = timezone(timedelta(hours=9))


def main():
    if len(sys.argv) < 2:
        print("사용: python scripts/save_brief.py <brief.json>", file=sys.stderr)
        sys.exit(1)
    brief = json.load(open(sys.argv[1], encoding="utf-8"))
    brief.setdefault("created_at", datetime.now(KST).strftime("%Y-%m-%d %H:%M"))

    path = os.path.join(DATA, "briefs.json")
    try:
        store = json.load(open(path, encoding="utf-8"))
    except Exception:
        store = {"briefs": []}
    brief["id"] = len(store["briefs"]) + 1
    store["briefs"].append(brief)
    json.dump(store, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"브리프 저장 #{brief['id']}: {brief.get('topic','?')} (총 {len(store['briefs'])}개)")


if __name__ == "__main__":
    main()
