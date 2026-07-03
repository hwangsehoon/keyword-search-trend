# 키워드 검색량 트렌드

네이버 공식 API(검색광고 + 데이터랩)로 키워드의 **일별 추정 검색량**을 조회하는 Streamlit 앱.
pluszero 키워드트렌드의 계산식을 그대로 재현하되, 브라우저·로그인 없이 순수 API 호출로 동작.

## 계산식

```
total       = pc + mo                       # 검색광고 getKeywordstat 월 PC/MO 검색수
daily[]     = 데이터랩 검색어트렌드 일별 비율 (2016-01-01~어제, 없는날 0)
last30Sum   = daily[-30:] 합
coefficient = total / last30Sum
그날 검색량  = round(daily[그날] * coefficient)
```

## 기능

- 키워드 최대 5개 동시 (쉼표 또는 줄바꿈 구분)
- 일간 / 주간 / 월간 / 연간 집계
- 빠른 기간(최근 3일 ~ 전체) + 직접 날짜 선택
- 데이터 표 / CSV 다운로드
- 선택형 비밀번호 게이트

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

`.streamlit/secrets.toml` 에 네이버 API 키가 있어야 함(레포에는 미포함).

## 배포 (Streamlit Community Cloud)

1. https://share.streamlit.io 접속 → GitHub 로그인
2. New app → 이 저장소 선택, main 브랜치, `app.py`
3. **Advanced settings → Secrets** 에 `.streamlit/secrets.toml` 내용을 그대로 붙여넣기
4. Deploy → `*.streamlit.app` 공개 주소 발급 (내 PC 꺼도 24시간 접속 가능)

## 자격증명 발급처

- 검색광고 API: searchad.naver.com → 도구 → API 사용 관리 (API_KEY / SECRET / CUSTOMER_ID)
- 데이터랩 오픈API: developers.naver.com (CLIENT_ID / CLIENT_SECRET)
