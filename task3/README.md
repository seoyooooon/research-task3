# Poster Archive 🎬 - 콘텐츠 시청 기록 포스터 달력

내가 시청한 영화, 드라마, 예능을 포스터 도장으로 캘린더에 기록하고 나만의 콘텐츠 시각적 아카이브를 구축할 수 있는 웹 애플리케이션 및 크롬 확장 프로그램입니다.

---

## 🚀 주요 기능

1. **시청 기록 CSV 가져오기**
   - 넷플릭스 등에서 다운로드한 시청 기록 CSV 파일을 업로드하여 달력에 즉시 시각화할 수 있습니다.
2. **TMDB API를 활용한 포스터 자동 매칭**
   - TMDB API를 연동하여 시청한 콘텐츠의 공식 포스터 이미지를 매칭하고 달력에 포스터 스탬프 형태로 표시합니다.
   - API 키가 없는 경우에도 데모(Mock) 데이터를 활용하여 시연이 가능합니다.
3. **PWA(Progressive Web App) 지원**
   - 서비스 워커(`sw.js`)와 앱 매니페스트(`manifest.json`)가 적용되어 있어 데스크톱 및 모바일에서 앱처럼 설치하여 오프라인으로 접근하고 원활하게 이용할 수 있습니다.
4. **아기자기한 동화책 풍 디자인("Lpalo")**
   - 따뜻한 주황색 계열의 아기자기한 색감, 둥글고 부드러운 테두리를 강조한 인터페이스를 탑재했습니다.
5. **크롬 확장 프로그램 연동**
   - 시청 기록 수집 및 관리의 편의를 위해 전용 크롬 익스텐션 패키지가 포함되어 있습니다.

---

## 📂 프로젝트 구조

```text
task3/
├── assets/                     # PWA용 아이콘 이미지 리소스
├── extension/                  # 크롬 확장 프로그램 패키지 (manifest v3)
│   ├── manifest.json           # 확장 프로그램 설정
│   ├── popup.html / popup.js   # 확장 프로그램 팝업 UI 및 로직
│   └── content.js              # 웹페이지 연동용 스크립트
├── index.html                  # 웹 애플리케이션 메인 페이지
├── style.css                   # 디자인 시스템 및 테마 스타일 시트
├── app.js                      # 데이터 파싱, TMDB API 연동, 달력 렌더링 로직
├── sw.js                       # Stale-While-Revalidate 캐싱 지원 서비스 워커
├── manifest.json               # PWA 매니페스트 설정
├── sample_netflix_records.csv  # 테스트용 샘플 CSV 데이터
├── test_parser.py / .js        # CSV 파서 검증을 위한 테스트 스크립트
└── antigravity_review.md       # AI 에이전트(Antigravity)를 활용한 개발 회고록
```

---

## 💻 실행 방법

### 1. 웹 애플리케이션 실행
- `task3/index.html` 파일을 더블클릭하여 브라우저에서 직접 열거나, 로컬 웹 서버(Live Server 등)를 통해 구동할 수 있습니다.
- 우측 상단 톱니바퀴 아이콘을 클릭하여 **TMDB API 키**를 설정하면 실시간 포스터 조회가 지원됩니다.

### 2. 크롬 확장 프로그램 등록 방법
1. 크롬 브라우저에서 `chrome://extensions/` 주소로 이동합니다.
2. 우측 상단의 **개발자 모드(Developer mode)**를 활성화합니다.
3. **압축해제된 확장 프로그램을 로드합니다(Load unpacked)** 버튼을 클릭합니다.
4. `task3/extension/` 폴더를 선택하여 등록합니다.

---

## 📝 개발 회고
AI 에이전트(**Antigravity**)와의 협업을 통해 디자인 시스템의 초고속 전환(어두운 네온 테마 → LPalo 테마), 반응형 레이아웃 보정, PWA 브라우저 캐싱 문제를 해결했습니다. 자세한 개발 여정과 활용 팁은 [antigravity_review.md](file:///c:/Users/megan/study-antigravity/research-task3/task3/antigravity_review.md)를 참고해 주세요.
