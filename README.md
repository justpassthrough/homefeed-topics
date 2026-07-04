# homefeed-topics

네이버 홈피드 **건강판**을 3일마다 로컬에서 스캔해, 지금 뜨는 **주제·훅·셀럽**을 자동 분석하고
누적 대시보드로 쌓는 도구. (검색 키워드 조합이 아니라, 실제 홈피드를 읽어 역산)

- 대시보드: https://justpassthrough.github.io/homefeed-topics/
- 스캔: `python scripts/scan_homefeed.py` (로컬 Playwright, 네이버는 Claude 내장도구 차단이라 로컬 필수)
- 대시보드 생성: `python scripts/build_dashboard.py`
- 텔레그램 리포트: `python scripts/make_report.py | python scripts/notify_telegram.py`
- 자동화: 작업스케줄러가 `run_homefeed_local.ps1`을 3일마다 실행

키워드 딥다이브(검색 상위노출용)와 **독립**. 이건 홈피드 전용.
