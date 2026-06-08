# -*- coding: utf-8 -*-
"""
얼굴 가상 시착을 활용한 TV 기능 확장 (Virtual Try-on & Smart TV Commerce Simulator)
- 실시간 카메라 입력 수신
- MediaPipe Tasks Face Landmarker를 통한 정교한 얼굴 추적
- EMA 필터를 적용한 떨림 방지
- 제품별 보정 스케일 및 오프셋 매핑
- 실시간 안경 피팅 크기(Scale) 및 수직 위치(Y-Offset) 미세 조정을 위한 트랙바(Trackbar) 연동
- 하단 UI 선택 카드 메뉴 및 주문 연동
- 프라이버시 보호를 위한 SF 스타일 아바타 페이스 모드 탑재
"""

import cv2
import numpy as np
import os
import time
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# ---------------------------------------------------------
# 1. 안경 상품 데이터베이스 정의
# ---------------------------------------------------------
GLASSES_DB = [
    {
        "id": 0,
        "name": "Classic Horn-Rimmed",
        "file": "horn_rimmed.png",
        "calib_scale": 1.75,   # 여백 크롭 완료에 부합하도록 1.75배로 조율
        "y_offset": 0.02,      # 안경이 위로 뜨지 않고 눈 위치에 안착하도록 오프셋 수정
        "brand": "RetroSpecs Co.",
        "material": "Eco-Acetate / Premium Handcrafted",
        "price": "$129.00",
        "desc": "지적이고 클래식한 분위기를 연출하는 베스트셀러 뿔테 안경"
    },
    {
        "id": 1,
        "name": "Modern Round Metal",
        "file": "metal_round.png",
        "calib_scale": 1.62,
        "y_offset": 0.18,      # 세로가 긴 메탈테 크기 특성에 맞춰 눈동자에 밀착 정렬
        "brand": "AeroTitan",
        "material": "Pure Beta-Titanium (Ultra Light)",
        "price": "$189.00",
        "desc": "티타늄 소재로 극도로 가벼운 착용감의 미니멀 원형 테"
    },
    {
        "id": 2,
        "name": "Fashion Red Sunglasses",
        "file": "red_sunglasses.png",
        "calib_scale": 1.90,
        "y_offset": 0.05,      # 눈부심 방지 핏에 적합한 눈동자 높이 매핑
        "brand": "VogueRay",
        "material": "Polarized UV400 / Acetate Red",
        "price": "$145.00",
        "desc": "트렌디한 레드 프레임과 UV 차단 편광 렌즈의 패션 선글라스"
    }
]

# ---------------------------------------------------------
# 2. 트랙바 안전 바인딩용 더미 콜백 함수
# ---------------------------------------------------------
def nothing(x):
    pass

# ---------------------------------------------------------
# 3. EMA (지수 이동 평균) 필터 클래스
# ---------------------------------------------------------
class EMAFilter:
    def __init__(self, alpha=0.2):
        self.alpha = alpha
        self.value = None
        
    def update(self, val):
        if self.value is None:
            self.value = val
        else:
            self.value = self.alpha * val + (1.0 - self.alpha) * self.value
        return self.value

# ---------------------------------------------------------
# 4. 투명 배경 이미지 오버레이 (알파 블렌딩) 함수
# ---------------------------------------------------------
def overlay_transparent(background, overlay, cx, cy):
    """
    투명 배경 PNG 이미지(overlay)를 배경 이미지(background)의 (cx, cy) 중심에 합성합니다.
    """
    h, w = overlay.shape[:2]
    # 좌상단 시작점 계산
    x_start = int(cx - w / 2)
    y_start = int(cy - h / 2)
    
    bg_h, bg_w = background.shape[:2]
    
    # overlay의 유효 클리핑 영역 산출
    x1_ov, x2_ov = 0, w
    y1_ov, y2_ov = 0, h
    
    if x_start < 0:
        x1_ov = -x_start
        x_start = 0
    if y_start < 0:
        y1_ov = -y_start
        y_start = 0
    if x_start + (x2_ov - x1_ov) > bg_w:
        x2_ov = x1_ov + (bg_w - x_start)
    if y_start + (y2_ov - y1_ov) > bg_h:
        y2_ov = y1_ov + (bg_h - y_start)
        
    # 합성할 공간의 폭/높이가 0 이하면 미합성
    if (x2_ov - x1_ov) <= 0 or (y2_ov - y1_ov) <= 0:
        return background
        
    crop_bg = background[y_start:y_start+(y2_ov-y1_ov), x_start:x_start+(x2_ov-x1_ov)]
    crop_ov = overlay[y1_ov:y2_ov, x1_ov:x2_ov]
    
    # 알파 채널 정규화 (0.0 ~ 1.0)
    alpha = crop_ov[:, :, 3] / 255.0
    alpha = np.expand_dims(alpha, axis=2)
    
    # 합성: BG = (1 - alpha) * BG + alpha * FG
    blended = (1.0 - alpha) * crop_bg + alpha * crop_ov[:, :, :3]
    background[y_start:y_start+(y2_ov-y1_ov), x_start:x_start+(x2_ov-x1_ov)] = blended.astype(np.uint8)
    return background

# ---------------------------------------------------------
# 5. 안경 크기 조절 및 회전 변환 함수
# ---------------------------------------------------------
def get_transformed_glasses(glasses_img, target_width, angle):
    """
    안경 이미지를 목표 너비로 조절하고 주어진 각도로 회전시킵니다.
    """
    h, w = glasses_img.shape[:2]
    aspect_ratio = h / w
    target_height = int(target_width * aspect_ratio)
    
    # 안전 장치: 너무 작거나 큰 크기 방지
    target_width = max(10, target_width)
    target_height = max(5, target_height)
    
    # 1단계: 크기 조절 (리사이즈)
    resized = cv2.resize(glasses_img, (target_width, target_height), interpolation=cv2.INTER_AREA)
    
    # 2단계: 회전 행렬 계산 및 회전
    center = (target_width // 2, target_height // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # 투명 채널 경계를 유지하며 회전 수행
    transformed = cv2.warpAffine(
        resized, M, (target_width, target_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(0, 0, 0, 0)
    )
    return transformed

# ---------------------------------------------------------
# 6. 글로벌 제어 변수 및 마우스 클릭 바인딩
# ---------------------------------------------------------
selected_glasses_idx = 0
order_status = "idle"  # "idle" -> "ordered" (주문 완료 알림 타이머용)
order_timer = 0

def mouse_callback(event, x, y, flags, param):
    global selected_glasses_idx, order_status, order_timer
    
    # 마우스 왼쪽 버튼 클릭 시
    if event == cv2.EVENT_LBUTTONDOWN:
        # 왼쪽 카메라 피팅 화면의 하단 UI 패널 영역 (y: 390~470) 터치 판정
        if 390 <= y <= 470:
            # 1번 카드: x: 20~200
            if 20 <= x <= 200:
                selected_glasses_idx = 0
                print("[UI] 1번 클래식 뿔테 안경 선택됨")
            # 2번 카드: x: 220~400
            elif 220 <= x <= 400:
                selected_glasses_idx = 1
                print("[UI] 2번 모던 라운드 메탈 안경 선택됨")
            # 3번 카드: x: 420~600
            elif 420 <= x <= 600:
                selected_glasses_idx = 2
                print("[UI] 3번 패션 레드 선글라스 선택됨")
        
        # 오른쪽 가상 TV/커머스 화면의 '주문하기' 버튼 판정
        # 전체 윈도우 기준 x: 640 + 400 ~ 640 + 580 (즉, 1040~1220), y: 380~430
        if 1040 <= x <= 1220 and 380 <= y <= 430:
            order_status = "ordered"
            order_timer = 60  # 약 3초 동안 주문 완료 팝업 표시 (20fps 기준)
            print("[COMMERCE] 안경 주문 완료 처리됨!")

# ---------------------------------------------------------
# 7. Face Landmarker 모델 자동 다운로드 함수
# ---------------------------------------------------------
def download_model_if_needed(model_path):
    if not os.path.exists(model_path):
        print("[INFO] MediaPipe Face Landmarker 모델 파일이 존재하지 않아 다운로드합니다...")
        url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            urllib.request.urlretrieve(url, model_path)
            print(f"[INFO] 모델 파일 다운로드 성공: {model_path}")
        except Exception as e:
            print(f"[ERROR] 모델 다운로드 중 에러 발생: {e}")
            raise e

# ---------------------------------------------------------
# 8. 메인 루프 실행부
# ---------------------------------------------------------
def main():
    global selected_glasses_idx, order_status, order_timer
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(current_dir, "assets")
    
    # 8.1 Face Landmarker .task 모델 자동 준비
    model_path = os.path.join(assets_dir, "face_landmarker.task")
    download_model_if_needed(model_path)
    
    # 8.2 투명 배경을 가진 안경 이미지 에셋 로드 (알파 채널 포함 BGRA 형태로 읽기)
    glasses_images = []
    for glass in GLASSES_DB:
        img_path = os.path.join(assets_dir, glass["file"])
        img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"[ERROR] 안경 에셋 파일 로드 실패: {img_path}")
            print("먼저 preprocess_assets.py 스크립트를 정상적으로 실행해 에셋을 변환하십시오.")
            return
        # 만약 알파 채널이 누락된 경우(3채널인 경우) 강제 4채널화
        if img.shape[2] == 3:
            b_ch, g_ch, r_ch = cv2.split(img)
            a_ch = np.ones(b_ch.shape, dtype=np.uint8) * 255
            img = cv2.merge([b_ch, g_ch, r_ch, a_ch])
        glasses_images.append(img)
        
    print("[INFO] 안경 에셋이 성공적으로 로드되었습니다.")
    
    # 8.3 윈도우 생성 및 마우스 콜백 등록
    win_name = "Smart TV - Virtual Try-on Shop"
    cv2.namedWindow(win_name)
    cv2.setMouseCallback(win_name, mouse_callback)
    
    # 실시간 피팅 스케일 조절을 위한 트랙바 생성 (범위: 70% ~ 200%, 초기치 100%)
    cv2.createTrackbar("Scale Adj (%)", win_name, 100, 200, nothing)
    cv2.setTrackbarPos("Scale Adj (%)", win_name, 100)
    
    # 실시간 피팅 수직 위치(Y) 조절을 위한 트랙바 생성 (범위: -60 ~ +60 픽셀, 초기치 60이 offset=0을 의미)
    cv2.createTrackbar("Y-Offset Adj", win_name, 60, 120, nothing)
    cv2.setTrackbarPos("Y-Offset Adj", win_name, 60)
    
    # 8.4 비디오 캡처 초기화 (웹캠 0번)
    cap = cv2.VideoCapture(0)
    webcam_available = True
    if not cap.isOpened():
        print("[WARNING] 카메라를 찾을 수 없습니다. 테스트를 위한 정적 아바타 모드로 실행됩니다.")
        webcam_available = False
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("[INFO] 웹캠 스트림이 초기화되었습니다.")

    # 8.5 MediaPipe Face Landmarker Tasks API 초기화
    base_options = python.BaseOptions(model_asset_path=model_path)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=False,
        output_facial_transformation_matrixes=False,
        num_faces=1
    )
    detector = vision.FaceLandmarker.create_from_options(options)
    print("[INFO] MediaPipe Face Landmarker Detector가 초기화되었습니다.")
    
    # 8.6 떨림 제어를 위한 EMA 필터 객체 초기화
    filter_x = EMAFilter(alpha=0.25)
    filter_y = EMAFilter(alpha=0.25)
    filter_w = EMAFilter(alpha=0.15)
    filter_a = EMAFilter(alpha=0.15)
    
    # 상태 플래그
    avatar_mode = False  # True인 경우 카메라 화면을 아바타 페이스 메시로 대체 (프라이버시 모드)
    frame_count = 0
    
    print("\n" + "="*50)
    print(" [컨트롤 안내]")
    print(" - [1, 2, 3 키] : 안경 제품 즉시 변경")
    print(" - [P 키]      : 프라이버시 아바타 피팅 모드 토글")
    print(" - [마우스클릭] : 하단 안경 카드 선택 및 TV '주문하기' 연동")
    print(" - [Scale 트랙바] : 안경 크기 실시간 조절")
    print(" - [Y-Offset 트랙바] : 안경 위아래 위치 실시간 조절")
    print(" - [ESC 키]    : 프로그램 정상 종료")
    print("="*50 + "\n")
    
    while True:
        frame_count += 1
        
        # 1. 프레임 취득
        if webcam_available:
            ret, frame = cap.read()
            if not ret:
                print("[ERROR] 카메라 프레임을 정상적으로 수신하지 못했습니다.")
                break
            frame = cv2.flip(frame, 1)  # 모니터 거울 효과 (좌우 반전)
        else:
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 40
            cv2.putText(frame, "Webcam Off (Static Test Mode)", (150, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
            cv2.putText(frame, "Connect webcam for live try-on.", (170, 280),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (130, 130, 130), 1)

        h_img, w_img, _ = frame.shape
        
        # 2. 트랙바 값 수집 및 가로 보정 스케일/수직 위치 가중치 도출
        try:
            user_scale_val = cv2.getTrackbarPos("Scale Adj (%)", win_name)
            if user_scale_val < 70:
                user_scale_val = 70
        except Exception:
            user_scale_val = 100
        user_scale = user_scale_val / 100.0
        
        try:
            user_y_val = cv2.getTrackbarPos("Y-Offset Adj", win_name) - 60  # -60 ~ +60 픽셀 오프셋
        except Exception:
            user_y_val = 0
            
        # 3. 미디어파이프 분석을 위한 RGB 변환 및 mp.Image 생성
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        
        # 4. 추론 실행
        detection_result = detector.detect(mp_image)
        
        face_detected = False
        
        # 5. 얼굴 랜드마크 분석 및 안경 합성
        if detection_result.face_landmarks:
            face_detected = True
            face_landmarks = detection_result.face_landmarks[0]
            
            # 아바타 모드 적용 시 실제 얼굴 가리기 (사이버 홀로그램 스캔 스타일)
            if avatar_mode:
                frame = np.ones((480, 640, 3), dtype=np.uint8) * 15  # 검은색 배경
                for lm in face_landmarks:
                    lm_x = int(lm.x * w_img)
                    lm_y = int(lm.y * h_img)
                    if 0 <= lm_x < w_img and 0 <= lm_y < h_img:
                        cv2.circle(frame, (lm_x, lm_y), 1, (0, 255, 120), -1)
            
            # 랜드마크 픽셀 좌표 획득 (왼쪽 눈 바깥 꼬리: 130, 오른쪽 눈 바깥 꼬리: 359)
            pl = face_landmarks[130]
            pr = face_landmarks[359]
            lx, ly = int(pl.x * w_img), int(pl.y * h_img)
            rx, ry = int(pr.x * w_img), int(pr.y * h_img)
            
            # 미간 중심점 (Landmark 168)
            pb = face_landmarks[168]
            bx, by = int(pb.x * w_img), int(pb.y * h_img)
            
            # 랜드마크 간 계산
            dx = rx - lx
            dy = ry - ly
            raw_eye_dist = np.sqrt(dx**2 + dy**2)
            raw_angle = -np.degrees(np.arctan2(dy, dx))  # 거울 반사 회전 보정
            
            # 현재 선택된 안경의 속성 로드
            current_glasses = GLASSES_DB[selected_glasses_idx]
            current_img = glasses_images[selected_glasses_idx]
            
            # 보정 스케일 및 사용자 수동 크기 조절값 적용하여 타겟 폭 결정
            raw_target_width = int(raw_eye_dist * current_glasses["calib_scale"] * user_scale)
            
            # 미간 위치에 안경의 수직 오프셋 보정 및 트랙바 수동 위치 오프셋 반영
            aspect_ratio = current_img.shape[0] / current_img.shape[1]
            raw_target_height = int(raw_target_width * aspect_ratio)
            raw_by = by + int(raw_target_height * current_glasses["y_offset"]) + user_y_val
            
            # 5.1 EMA 필터를 통한 떨림 억제
            smooth_cx = int(filter_x.update(bx))
            smooth_cy = int(filter_y.update(raw_by))
            smooth_w = int(filter_w.update(raw_target_width))
            smooth_a = filter_a.update(raw_angle)
            
            # 5.2 이미지 변환 및 합성
            transformed_glasses = get_transformed_glasses(current_img, smooth_w, smooth_a)
            frame = overlay_transparent(frame, transformed_glasses, smooth_cx, smooth_cy)
            
        else:
            filter_x.value = None
            filter_y.value = None
            filter_w.value = None
            filter_a.value = None
            
            if avatar_mode:
                frame = np.ones((480, 640, 3), dtype=np.uint8) * 15
            
            cv2.rectangle(frame, (120, 200), (520, 280), (0, 0, 150), -1)
            cv2.rectangle(frame, (120, 200), (520, 280), (0, 0, 255), 2)
            cv2.putText(frame, "DETECTING FACE LANDMARKS...", (145, 235),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(frame, "Please align your face to camera", (180, 262),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # ---------------------------------------------------------
        # 8. 왼쪽 카메라 뷰 하단 UI 패널 드로잉 (제품 선택 영역)
        # ---------------------------------------------------------
        ui_overlay = frame.copy()
        cv2.rectangle(ui_overlay, (0, 380), (640, 480), (20, 20, 20), -1)
        cv2.addWeighted(ui_overlay, 0.85, frame, 0.15, 0, frame)
        
        cv2.line(frame, (0, 380), (640, 380), (80, 80, 80), 1)
        
        card_w = 180
        gap = 20
        start_x = 20
        
        for idx, glass in enumerate(GLASSES_DB):
            x1 = start_x + idx * (card_w + gap)
            y1 = 390
            x2 = x1 + card_w
            y2 = 470
            
            if idx == selected_glasses_idx:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 120), 2)
                bg_color = (40, 60, 40)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (60, 60, 60), 1)
                bg_color = (25, 25, 25)
                
            cv2.rectangle(frame, (x1+2, y1+2), (x2-2, y2-2), bg_color, -1)
            
            cv2.putText(frame, f"{idx+1}. {glass['name']}", (x1+10, y1+25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, glass["brand"], (x1+10, y1+45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1, cv2.LINE_AA)
            cv2.putText(frame, glass["price"], (x1+10, y1+65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 120), 1, cv2.LINE_AA)

        # ---------------------------------------------------------
        # 9. 오른쪽 가상 스마트 TV 및 커머스 주문 화면 드로잉 (640x480)
        # ---------------------------------------------------------
        tv_canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        tv_canvas[:] = (30, 25, 20)
        
        cv2.rectangle(tv_canvas, (10, 10), (630, 470), (120, 120, 120), 2)
        cv2.rectangle(tv_canvas, (15, 15), (625, 465), (10, 10, 10), -1)
        
        cv2.rectangle(tv_canvas, (15, 15), (625, 75), (25, 30, 50), -1)
        cv2.putText(tv_canvas, "SMART TV SHOWPING - VIRTUAL FIT-ROOM", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(tv_canvas, "Live Virtual Try-On Integration", (50, 68),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 200), 1, cv2.LINE_AA)
        
        selected_prod = GLASSES_DB[selected_glasses_idx]
        
        cv2.putText(tv_canvas, "PRODUCT PROFILE", (35, 115),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 180, 180), 1, cv2.LINE_AA)
        cv2.line(tv_canvas, (35, 125), (600, 125), (50, 50, 50), 1)
        
        cv2.putText(tv_canvas, f"Product Name : {selected_prod['name']}", (35, 155),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(tv_canvas, f"Brand        : {selected_prod['brand']}", (35, 190),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(tv_canvas, f"Material     : {selected_prod['material']}", (35, 220),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(tv_canvas, f"Price        : {selected_prod['price']}", (35, 255),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2, cv2.LINE_AA)
        
        cv2.putText(tv_canvas, "Description:", (35, 290),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1, cv2.LINE_AA)
        
        desc_en = {
            0: "Timeless luxury frame. Enhances facial contours elegantly.",
            1: "Extremely lightweight titanium wire frame for peak comfort.",
            2: "Vibrant and retro styling sunglasses for outdoor activity."
        }[selected_glasses_idx]
        
        cv2.putText(tv_canvas, desc_en, (35, 315),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1, cv2.LINE_AA)
        
        # 실시간 수동 튜닝 조절값 피드백 텍스트
        cv2.putText(tv_canvas, f"Fit Scale Offset: {user_scale_val}%", (35, 345),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(tv_canvas, f"Fit Y-Offset    : {user_y_val} px", (35, 362),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1, cv2.LINE_AA)
        
        # ----------------- UI 액션 버튼 (주문하기) -----------------
        btn_x1, btn_y1 = 400, 380
        btn_x2, btn_y2 = 580, 430
        
        cv2.rectangle(tv_canvas, (btn_x1, btn_y1), (btn_x2, btn_y2), (0, 180, 80), -1)
        cv2.rectangle(tv_canvas, (btn_x1, btn_y1), (btn_x2, btn_y2), (255, 255, 255), 1)
        cv2.putText(tv_canvas, "ORDER NOW", (btn_x1+25, btn_y1+32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)
        
        help_color = (0, 200, 255) if avatar_mode else (150, 150, 150)
        mode_str = "AVATAR (ON)" if avatar_mode else "CAMERA (NORMAL)"
        cv2.putText(tv_canvas, f"FITTING MODE: {mode_str} (Press 'P' to Toggle)", (35, 395),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, help_color, 1, cv2.LINE_AA)
        cv2.putText(tv_canvas, "Press [1, 2, 3] to switch  |  [ESC] to Exit", (35, 420),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1, cv2.LINE_AA)
        
        # ----------------- 주문 성공 팝업 알림 -----------------
        if order_status == "ordered":
            if order_timer > 0:
                order_timer -= 1
                cv2.rectangle(tv_canvas, (100, 180), (540, 320), (20, 20, 20), -1)
                cv2.rectangle(tv_canvas, (100, 180), (540, 320), (0, 255, 120), 2)
                cv2.putText(tv_canvas, "ORDER SUCCESSFUL!", (165, 235),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2, cv2.LINE_AA)
                cv2.putText(tv_canvas, f"Your {selected_prod['name']} is preparing.", (130, 275),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)
            else:
                order_status = "idle"

        # ---------------------------------------------------------
        # 10. 화면 병합 및 윈도우 송출
        # ---------------------------------------------------------
        combined_view = np.hstack((frame, tv_canvas))
        cv2.imshow(win_name, combined_view)
        
        key = cv2.waitKey(40) & 0xFF
        
        if key == 27:  # ESC
            print("[INFO] ESC 키가 입력되어 프로그램을 안전하게 종료합니다.")
            break
        elif key == ord('1'):
            selected_glasses_idx = 0
            print("[KEY] 1번 클래식 뿔테 안경 선택됨")
        elif key == ord('2'):
            selected_glasses_idx = 1
            print("[KEY] 2번 모던 라운드 메탈 안경 선택됨")
        elif key == ord('3'):
            selected_glasses_idx = 2
            print("[KEY] 3번 패션 레드 선글라스 선택됨")
        elif key == ord('p') or key == ord('P'):
            avatar_mode = not avatar_mode
            print(f"[KEY] 아바타 모드 상태 변경: {avatar_mode}")

    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
