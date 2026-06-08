# 얼굴 가상 시착을 활용한 TV 기능 확장 (Virtual Try-on & Smart TV Commerce)

본 프로젝트는 MediaPipe Face Mesh 및 OpenCV를 기반으로 사용자의 얼굴을 실시간 추적하여 선택한 안경 제품을 얼굴 위에 오버레이하고, 스마트 TV의 커머스 쇼핑 채널과 연동하는 가상 피팅 룸 솔루션입니다.

---

## 📂 폴더 구조
```text
tasks/task2/
├── assets/                  # 이미지 에셋 폴더
│   ├── raw_horn_rimmed.png  # 원본 뿔테 이미지
│   ├── raw_metal_round.png  # 원본 둥근 테 이미지
│   ├── raw_red_sunglasses.png # 원본 선글라스 이미지
│   ├── horn_rimmed.png      # 배경 투명화 전처리 완료 에셋
│   ├── metal_round.png      # 배경 투명화 전처리 완료 에셋
│   └── red_sunglasses.png   # 배경 투명화 전처리 완료 에셋
├── preprocess_assets.py     # 이미지 에셋 알파 채널 전처리 스크립트
├── virtual_tryon.py         # 실시간 가상 시착 & 스마트 TV 메인 실행 스크립트
└── README.md                # 사용 설명서 (본 파일)
```

---

## 🛠️ 개발 환경 및 요구사항
- Python 3.13.5 (혹은 Python 3.8 이상 호환 가능)
- OpenCV Python (`opencv-python`)
- MediaPipe (`mediapipe`)
- NumPy (`numpy`)

### 패키지 설치 방법
```bash
pip install opencv-python mediapipe numpy
```

---

## 🚀 실행 가이드

### 1단계: 안경 에셋 투명화 전처리 실행
AI가 생성한 원본 안경 사진들의 흰색 배경을 투명하게 만들어주는 전처리를 먼저 수행합니다.
```bash
python preprocess_assets.py
```
- 실행 후 `assets/` 디렉토리에 알파 채널(투명 배경)이 포함된 `horn_rimmed.png`, `metal_round.png`, `red_sunglasses.png` 파일이 자동 생성됩니다.

### 2단계: 메인 프로그램 실행
실시간 얼굴 추적 가상 시착 데모 및 스마트 TV 시뮬레이션을 실행합니다.
```bash
python virtual_tryon.py
```

---

## 🎮 주요 조작 및 기능 설명

### 1. 가상 시착 제품 변경 (Try-On Selector)
- **키보드 단축키**: `1`, `2`, `3` 키를 눌러 안경 종류를 즉시 교체할 수 있습니다.
  - **1번**: Classic Horn-Rimmed (클래식 뿔테 안경)
  - **2번**: Modern Round Metal (모던 라운드 메탈 안경)
  - **3번**: Fashion Red Sunglasses (패션 레드 선글라스)
- **마우스 클릭**: 실시간 피팅 카메라 뷰의 하단 카드 UI 영역을 마우스로 클릭하여 안경을 선택할 수 있습니다.

### 2. 스마트 TV 주문 연동 (Smart TV Commerce Integration)
- 우측 가상 스마트 TV 화면의 **[ORDER NOW]** 버튼 영역을 마우스로 클릭하면 주문 프로세스가 구동됩니다.
- 주문 성공 시 화면 중앙에 화려한 그린 컬러의 "ORDER SUCCESSFUL!" 팝업 애니메이션이 3초간 발생합니다.

### 3. 프라이버시 보호를 위한 아바타 모드 (Avatar Try-On Mode)
- **키보드 `P` / `p` 키**를 누르면 실제 웹캠 비디오 송출을 숨기고, 어두운 가상 공간 상에 MediaPipe Face Mesh의 점과 선들로 구조화된 **네온 사이버 스타일 아바타 페이스** 위에 안경을 착용해 볼 수 있습니다. 얼굴 노출 없이 안경 형상 피팅감을 체크하기 좋습니다.

### 4. 프로그램 종료
- **ESC 키**를 누르면 안전하게 모든 리소스를 반환하고 프로그램을 종료합니다.

---

## 💡 주요 구현 기술
1. **MediaPipe Face Mesh (Refined Landmarks)**:
   - 미간 중심점(`Landmark 168`), 눈 좌우 바깥 꼬리(`130`, `359`)를 사용하여 얼굴의 회전 각도(Roll) 및 물리적 거리 비례 너비를 실시간으로 유도해 안경 회전/스케일 변환을 정밀 수행합니다.
2. **지수 이동 평균 (EMA) 필터링**:
   - 카메라 미세 진동 및 조명 변화로 인한 랜드마크 지점 떨림 현상을 해소하기 위해 위치/각도/너비 데이터에 EMA 필터를 적용하여 미끄러지듯 부드럽게 오버레이를 유지합니다.
3. **제품별 맞춤 스케일 및 오프셋**:
   - 제품별 고유 가로/세로 기하 비율에 대응하기 위해 `calib_scale` 및 미간 수직 보정 오프셋 `y_offset`을 구성하여 어떤 안경이든 눈 위치에 일관되게 장착되도록 정밀 보정했습니다.
