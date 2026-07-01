# 나라장터 낙찰정보 대시보드 개발 대화 기록

## 프로젝트 개요
- **목적**: 조달청_나라장터 낙찰정보서비스(용역) OpenAPI를 이용한 낙찰정보 대시보드
- **배경**: 기존 `g2b_dashboard`(입찰공고·사전규격 검색 대시보드)와는 별도로, 이미 낙찰이 끝난 건의 **낙찰자·낙찰금액·낙찰율**을 분석하기 위해 신규 제작
- **기술 스택**: Python + Streamlit, 나라장터 OpenAPI (개인 API 인증키는 기존 g2b_dashboard와 동일한 키 재사용)
- **작업 디렉터리**: `C:\Users\82104\g2b_scsbid_dashboard\`

---

## 주요 파일 구성

| 파일 | 역할 |
|------|------|
| `app.py` | Streamlit 메인 앱 (UI, 필터, 테이블, 낙찰자 순위, 통계) |
| `api_client.py` | 나라장터 낙찰정보서비스 API 연동, 데이터 정규화 |
| `search.xlsx` | 우선순위 키워드 프리셋 (g2b_dashboard와 동일 파일 재사용) |
| `.env` | API 키 저장 (`G2B_API_KEY=...`, git에는 미포함) |

---

## API 정보

- **엔드포인트**: `http://apis.data.go.kr/1230000/as/ScsbidInfoService/getScsbidListSttusServcPPSSrch` (용역 부문 낙찰정보)
- **필드명 확인 방법**: 문서만 보고 추측하지 않고, 실제 API를 직접 호출해 응답 필드를 확인 후 매핑 (사전규격 API 때 필드명 추측으로 버그가 났던 전례 → `ipchal.md` 참고)
- **주요 응답 필드**:
  - `bidNtceNo` / `bidNtceOrd` → 공고번호 / 공고차수
  - `bidNtceNm` → 공고명
  - `dminsttNm` → 수요기관
  - `prtcptCnum` → 참가업체수
  - `bidwinnrNm` → 낙찰자
  - `bidwinnrBizno` / `bidwinnrCeoNm` / `bidwinnrAdrs` / `bidwinnrTelNo` → 낙찰자 사업자번호/대표자/주소/연락처
  - `sucsfbidAmt` → 낙찰금액
  - `sucsfbidRate` → 낙찰율 (일부 건은 빈 문자열 → NaN 처리)
  - `rlOpengDt` → 개찰일시
  - `rgstDt` → 등록일시
  - `fnlSucsfDate` → 최종낙찰일자
- **키워드 검색**: `bidNtceNm` 파라미터로 서버 사이드 키워드 필터링 가능 (입찰공고 API와 동일한 방식)
- **업무구분**: 사용자 요청에 따라 **용역만** 구현 (물품 `getScsbidListSttusThngPPSSrch`, 공사 `getScsbidListSttusCnstwkPPSSrch` 엔드포인트도 동일 구조로 존재하나 미구현)

---

## 개발 과정

### 1. 기존 프로젝트 구조 파악
- `g2b_dashboard`의 `api_client.py`, `app.py`, `.env`, `.gitignore`, `requirements.txt`, `runtime.txt` 구조를 참고
- `search.xlsx` 우선순위 키워드 프리셋(대표님/1순위/2순위/3순위)을 그대로 재사용하기로 결정

### 2. API 실제 호출로 필드 검증
- curl로 `ScsbidInfoService`의 용역/물품/공사 엔드포인트를 직접 호출해 실제 JSON 응답 확인
- `bidNtceNm` 키워드 파라미터가 정상 동작함을 확인 후 서버사이드 필터링 채택

### 3. `api_client.py` 구현
- `fetch_scsbid()`: 키워드별 OR 검색 → 페이지네이션 → 병합 → 공고번호+공고차수 기준 중복 제거 → 최소낙찰금액/제외키워드 필터 → 개찰일시 기준 정렬

### 4. `app.py` 구현 (기존 검색 대시보드와 차별화)
- 조회조건: 우선순위 키워드 멀티셀렉트(search.xlsx), 추가 키워드, 최소 낙찰금액, 개찰일 기준 조회기간, 제외 키워드
- **📋 전체 목록** 탭: 개찰일·공고명·수요기관·낙찰자·낙찰금액·낙찰율·참가업체수·연락처, 결과 내 검색/정렬/CSV 다운로드
- **🏆 낙찰자 순위** 탭 (신규 기능): 낙찰 건수/금액 합계 상위 낙찰자 차트 + 낙찰자별 상세 요약표 (경쟁사 수주 현황 분석용)
- **📊 통계** 탭: 수요기관별 건수, 낙찰금액/낙찰율 구간 분포, 일자별 낙찰 추이

### 5. 로컬 테스트
- `pip install -r requirements.txt` 후 `python -c` 로 `fetch_scsbid()` 직접 호출 → 실제 데이터 정상 반환 확인 (터미널 한글 인코딩 깨짐은 cp949 콘솔 표시 문제일 뿐 실제 데이터는 정상)
- `streamlit run app.py --server.port 8503` 로컬 실행 후 Claude in Chrome으로 브라우저 UI 테스트
  - "경로당" 키워드, 30일 조회 → 9건, 메트릭 카드(전체 낙찰 건수/총 낙찰금액/평균 낙찰율/평균 참가업체수) 정상 표시
  - 낙찰자 순위 탭 차트 및 상세표 정상 동작 확인
  - 테스트 중 Chrome 자동번역 기능이 페이지를 오작동 번역(락찰정보, 소수점금액 등 오역)하는 현상 발견 → 새로고침으로 재현되지 않음을 확인, 실제 코드 문제 아님

### 6. GitHub 배포
- `gh repo create sang2wr/g2b-scsbid-dashboard --public` 으로 신규 저장소 생성 (사용자 승인 후 진행)
- `.env`는 `.gitignore`로 제외, 나머지 파일 커밋 후 push

### 7. Streamlit Community Cloud 배포
- share.streamlit.io에서 기존 sang2wr 계정으로 신규 앱 생성
- 저장소: `sang2wr/g2b-scsbid-dashboard`, 브랜치: `master`, 메인 파일: `app.py`
- **고급 설정**에서 Secrets에 `G2B_API_KEY` 등록 (TOML 형식), Python 버전 3.11로 지정 (runtime.txt와 일치)
- 배포 후 클라우드 URL에서도 "경로당" 키워드 조회 테스트 → 로컬과 동일하게 9건 정상 조회 확인

---

## 배포 정보

- **GitHub 저장소**: https://github.com/sang2wr/g2b-scsbid-dashboard
- **배포 플랫폼**: Streamlit Community Cloud
- **배포 URL**: https://g2b-scsb-hrywkltgtmwxzt4etzuwcm.streamlit.app/
- **배포 완료일**: 2026-07-01

---

## 실행 방법

```powershell
cd C:\Users\82104\g2b_scsbid_dashboard
python -m streamlit run app.py --server.port 8503
```

브라우저에서 `http://localhost:8503` 접속

---

## 향후 참고 사항

1. **물품·공사 부문 확장 시**: `getScsbidListSttusThngPPSSrch`(물품), `getScsbidListSttusCnstwkPPSSrch`(공사) 엔드포인트가 용역과 동일한 응답 구조를 가지므로, `api_client.py`에 업무구분 파라미터만 추가하면 확장 가능
2. **낙찰율 결측치**: 일부 건(수의계약 등)은 `sucsfbidRate`가 빈 문자열로 응답되어 화면에 "None"으로 표시됨 — 정상 동작이며 API 원본 데이터의 특성
3. **Chrome 자동번역 이슈**: 테스트 환경에서 간헐적으로 한글 페이지를 다른 한글로 오역하는 현상 발생 가능 — 새로고침하면 해결되는 브라우저 측 일시적 현상으로, 앱 코드와 무관

*기록 생성일: 2026-07-01*
