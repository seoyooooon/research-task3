# AI 에이전트(Antigravity) 활용 개발 회고록
> **과제명:** AI 에이전트를 활용한 콘텐츠 시청 기록 포스터 달력  
> **작성일:** 2026년 6월 21일 (3주차 진행 중)

개발 과정에서 AI 에이전트(**Antigravity**)를 활발히 도입하며 느낀 점들을 부문별로 정리한 내용입니다.

---

## 1. 🚀 놀라운 개발 속도 및 생산성 향상
* **초고속 디자인 시스템 전환**: 
  - 어두운 네온 테마에서 스위스 스타일의 미니멀 미노크롬 테마("Programa"), 그리고 최종적으로 주황색 기반의 아기자기한 동화책 스타일("Lpalo") 테마로의 전반적인 UI 디자인 수정이 단 몇 분 만에 완벽히 구현되었습니다.
  - 수작업으로 변경했다면 수시간이 걸렸을 대량의 CSS 변수, 테두리 두께, 둥글기 값 조율이 원클릭 수준으로 단축되었습니다.
* **풀스택 및 멀티 플랫폼 동시 개발**:
  - 웹 프론트엔드 코드([index.html](file:///c:/Users/megan/study-antigravity/research-task3/task3/index.html), [style.css](file:///c:/Users/megan/study-antigravity/research-task3/task3/style.css)) 수정과 연동용 파이썬 유닛 테스트 작성([test_parser.py](file:///c:/Users/megan/study-antigravity/research-task3/task3/test_parser.py))은 물론이고, 크롬 확장 프로그램([extension/manifest.json](file:///c:/Users/megan/study-antigravity/research-task3/task3/extension/manifest.json))까지 일관성 있게 일괄 구현되었습니다.

## 2. 🔍 자율적 문제 해결 및 디버깅 능력
* **PWA 서비스 워커 캐시 문제 해결**:
  - 스타일을 변경했으나 브라우저 캐시 때문에 갱신되지 않는 현상이 발생했을 때, 에이전트가 캐시 정책([sw.js](file:///c:/Users/megan/study-antigravity/research-task3/task3/sw.js))의 'Stale-While-Revalidate' 동작을 자율적으로 파악해 내고 HTML 내 링크에 버전 파라미터(`style.css?v=7`)를 붙여 똑똑하게 해결했습니다.
* **유연한 환경 대처**:
  - 로컬 브라우저 에이전트를 가동해 디자인을 직접 스캔하고 스크롤 가능 여부를 체크했습니다.
  - 테스트용 Node.js 환경이 미설치된 것을 감지하자마자, 파이썬 기반 테스트 스크립트([test_extension.py](file:///C:/Users/megan/.gemini/antigravity-ide/brain/f2c8d250-08e3-4af4-ac63-020e8450f110/scratch/test_extension.py))를 즉시 작성해 파싱 알고리즘을 성공적으로 검증했습니다.

## 3. 🎨 세밀한 사용자 피드백 반영
* **커스텀 가로/세로 레이아웃 보정**:
  - "100% 줌 상태에서 달력이 한눈에 차게 해달라"는 요구에 맞게 데스크톱 브라우저 높이(`100vh`)에 맞춘 반응형 자동 늘림 그리드를 구성하고, 모바일에서는 스크롤이 정상 작동하도록 설계했습니다.
  - "요일 서체 키우기", "날짜 두껍게 변경", "주말 요일 색상 지정(토요일 파랑, 일요일 빨강)" 등 세세한 디자인 피드백이 완벽히 코드로 치환되었습니다.

## 4. 💡 종합적인 시사점
* **기존 개발 방식과의 차이**:
  - 기존에는 문서를 보며 하나씩 코딩하고 에러를 디버깅하는 순차적 방식이었다면, Antigravity 협업 방식은 **'목표와 요구사항을 구체적으로 설명(Grill-me 등)하고 에이전트가 넓은 범위를 일시에 조율하는 선언적 개발'**에 가깝습니다.
* **에이전트 활용 팁**:
  - 구체적인 수치(예: 720px 너비, 특정 색상 코드)와 명확한 디자인 지표("Lpalo 스타일 토큰")를 제공했을 때 최상의 시각적 퀄리티를 도출해 낼 수 있었습니다.
