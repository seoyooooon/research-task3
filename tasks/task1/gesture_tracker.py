# -*- coding: utf-8 -*-
"""
카메라 기반 컬러 스티커 추적 및 제스처 인식 스마트 TV 제어 시스템 (Revision 1)
(Gesture Recognition & Smart TV Simulator using OpenCV)
"""

import cv2
import numpy as np
from collections import deque
import time

# ---------------------------------------------------------
# 1. 초기 설정 및 가상 TV 채널 정보
# ---------------------------------------------------------
CHANNELS = [
    {"num": 7, "name": "KBS1", "show": "9 O'clock News (Live)", "theme": "news"},
    {"num": 9, "name": "KBS2", "show": "Music Bank (K-POP)", "theme": "music"},
    {"num": 11, "name": "MBC", "show": "Running Man (Variety)", "theme": "variety"},
    {"num": 13, "name": "SBS", "show": "Inkigayo (Music Show)", "theme": "inkigayo"},
    {"num": 24, "name": "YTN", "show": "24h Breaking News", "theme": "ytn"}
]

current_channel_idx = 0
volume = 30  # 0 ~ 100 범위
tv_power = True

# 스마트 TV 홈 화면(스마트 허브) 상태 변수
is_home_mode = False
apps = ["Netflix", "YouTube", "Disney+", "Settings"]
selected_app_idx = 0
is_app_running = False
running_app_name = ""

# ---------------------------------------------------------
# 2. 마우스 시뮬레이션 설정 (카메라가 없거나 보정 전용)
# ---------------------------------------------------------
use_mouse_sim = False
mouse_x, mouse_y = 320, 240
mouse_active = False

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y, mouse_active
    # 메인 윈도우의 왼쪽 절반(카메라 영역: 640x480)에서만 마우스 위치 수집
    if x < 640:
        mouse_x, mouse_y = x, y
        if event == cv2.EVENT_LBUTTONDOWN:
            mouse_active = True
        elif event == cv2.EVENT_LBUTTONUP:
            mouse_active = False

# ---------------------------------------------------------
# 3. HSV 색상 조절용 트랙바 안전값 리딩 헬퍼 함수
# ---------------------------------------------------------
def nothing(x):
    pass

def get_trackbar_val(trackbar_name, win_name, default_val):
    try:
        # 창이 유효한지 확인하고 값 읽기
        if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) >= 0:
            val = cv2.getTrackbarPos(trackbar_name, win_name)
            if val == -1:
                return default_val
            return val
    except cv2.error:
        pass
    return default_val

# ---------------------------------------------------------
# 4. 메인 프로그램 시작
# ---------------------------------------------------------
def main():
    global current_channel_idx, volume, use_mouse_sim, mouse_x, mouse_y, mouse_active
    global is_home_mode, selected_app_idx, is_app_running, running_app_name
    
    # 메인 윈도우 생성
    win_name = "Smart TV Gesture Controller"
    cv2.namedWindow(win_name)
    cv2.setMouseCallback(win_name, mouse_callback)

    # 컨트롤 패널 윈도우 생성 및 트랙바 부착
    ctrl_win = "Control Panel (Color Calibration)"
    cv2.namedWindow(ctrl_win)
    cv2.resizeWindow(ctrl_win, 400, 350)
    
    # 트랙바 초기화 (연두색 스티커 디폴트 범위)
    cv2.createTrackbar("Min H", ctrl_win, 35, 179, nothing)
    cv2.createTrackbar("Max H", ctrl_win, 85, 179, nothing)
    cv2.createTrackbar("Min S", ctrl_win, 60, 255, nothing)
    cv2.createTrackbar("Max S", ctrl_win, 255, 255, nothing)
    cv2.createTrackbar("Min V", ctrl_win, 60, 255, nothing)
    cv2.createTrackbar("Max V", ctrl_win, 255, 255, nothing)

    # 윈도우 인스턴스 갱신을 위해 waitKey를 즉시 실행
    cv2.waitKey(1)

    # 비디오 캡처 초기화 (기본 웹캠 0번 사용)
    cap = cv2.VideoCapture(0)
    
    webcam_available = True
    if not cap.isOpened():
        print("[WARNING] 웹캠을 열 수 없습니다. 마우스 시뮬레이션 모드로 시작합니다.")
        webcam_available = False
        use_mouse_sim = True
    else:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        print("[INFO] 웹캠이 연결되었습니다. 'm' 키로 마우스 모드로 전환할 수 있습니다.")

    # 궤적 저장을 위한 덱(deque) 초기화 (최대 20프레임)
    pts = deque(maxlen=20)
    
    # 제스처 제어 관련 변수
    cooldown_counter = 0
    active_gesture = None
    gesture_display_timer = 0
    
    # 주워들기 동작 오인식 방지를 위한 지속 추적 프레임 수 카운터
    tracking_active_frames = 0
    
    # 스냅 및 흔들기 판단 임계값 설정
    SNAP_DIST_THRESHOLD_X = 80   # 좌우 이동 픽셀 기준
    SNAP_DIST_THRESHOLD_Y = 60   # 상하 이동 픽셀 기준
    SNAP_FRAME_WINDOW = 6        # 현재 프레임과 비교할 과거 프레임 창 크기
    
    frame_count = 0

    while True:
        frame_count += 1
        sticker_tracked = False

        # 메인 윈도우가 강제 종료되었는지 검사하여 예외 없이 자연스럽게 루프 이탈
        try:
            if cv2.getWindowProperty(win_name, cv2.WND_PROP_VISIBLE) < 1:
                print("[INFO] 메인 윈도우가 닫혀 프로그램을 종료합니다.")
                break
        except cv2.error:
            pass

        # 쿨다운 및 제스처 텍스트 타이머 감소
        if cooldown_counter > 0:
            cooldown_counter -= 1
        if gesture_display_timer > 0:
            gesture_display_timer -= 1
        else:
            active_gesture = None

        # 프레임 준비
        if webcam_available and not use_mouse_sim:
            ret, cam_frame = cap.read()
            if not ret:
                print("[ERROR] 카메라 프레임을 읽어오지 못했습니다. 마우스 모드로 자동 전환합니다.")
                use_mouse_sim = True
                continue
            cam_frame = cv2.flip(cam_frame, 1) # 좌우 반전
            
            # 사용자 얼굴이 노출되지 않도록 표시용 화면은 순수 흰색으로 덮어씀
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
        else:
            cam_frame = None
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 255
            cv2.putText(frame, "Mouse Simulation Mode", (20, 50), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (180, 50, 0), 2)
            cv2.putText(frame, "Click & Drag mouse inside here", (20, 80), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)
            cv2.putText(frame, "Press 'm' to switch to Camera Mode", (20, 110), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 80, 80), 1)

        # ---------------------------------------------------------
        # 5. 객체 추적 (색상 기반 또는 마우스 시뮬레이션)
        # ---------------------------------------------------------
        cx, cy = None, None

        if use_mouse_sim:
            cx, cy = mouse_x, mouse_y
            sticker_tracked = True
            cv2.circle(frame, (cx, cy), 12, (0, 255, 0), -1)
            cv2.circle(frame, (cx, cy), 15, (0, 0, 0), 2) # 테두리를 흰색 대신 검은색으로 변경
        else:
            # 안전하게 트랙바 값 읽기 (크래시 방지)
            min_h = get_trackbar_val("Min H", ctrl_win, 35)
            max_h = get_trackbar_val("Max H", ctrl_win, 85)
            min_s = get_trackbar_val("Min S", ctrl_win, 60)
            max_s = get_trackbar_val("Max S", ctrl_win, 255)
            min_v = get_trackbar_val("Min V", ctrl_win, 60)
            max_v = get_trackbar_val("Max V", ctrl_win, 255)
            
            # 실시간 컬러 트래킹은 백그라운드 카메라인 cam_frame으로 분석
            hsv = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2HSV)
            lower_bound = np.array([min_h, min_s, min_v])
            upper_bound = np.array([max_h, max_s, max_v])
            
            mask = cv2.inRange(hsv, lower_bound, upper_bound)
            
            # 노이즈 필터링
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if len(contours) > 0:
                largest_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(largest_contour)
                
                if area > 400:
                    M = cv2.moments(largest_contour)
                    if M["m00"] > 0:
                        cx = int(M["m10"] / M["m00"])
                        cy = int(M["m01"] / M["m00"])
                        sticker_tracked = True
                        
                        # 흰색 피드백 화면(frame)에 추적 정보 시각화
                        x, y, w, h = cv2.boundingRect(largest_contour)
                        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                        cv2.circle(frame, (cx, cy), 8, (0, 0, 255), -1)
            
            # 타겟 감지가 유실되었을 때 흰 화면 상에 프라이버시 모드 안내 메시지 표시
            if not sticker_tracked:
                cv2.putText(frame, "Privacy Mode Active (Camera Hidden)", (50, 220), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 50, 50), 2)
                cv2.putText(frame, "Show color sticker to track", (180, 260), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 120, 120), 1)
            
            # 보정 창이 열려있을 때만 마스크 영상 업데이트
            try:
                if cv2.getWindowProperty(ctrl_win, cv2.WND_PROP_VISIBLE) >= 1:
                    resized_mask = cv2.resize(mask, (320, 240))
                    cv2.imshow(ctrl_win, resized_mask)
            except cv2.error:
                pass

        # ---------------------------------------------------------
        # 6. 지속 추적 프레임 계산 (주워들기 오인식 필터링)
        # ---------------------------------------------------------
        if sticker_tracked:
            pts.appendleft((cx, cy))
            tracking_active_frames += 1
        else:
            # 추적 실패 시 궤적 순차 삭제 및 활성 프레임 리셋
            if len(pts) > 0:
                pts.pop()
            tracking_active_frames = 0

        # 궤적 그리기
        for i in range(1, len(pts)):
            if pts[i - 1] is None or pts[i] is None:
                continue
            thickness = int(np.sqrt(20 / float(i + 1)) * 2.5) + 1
            cv2.line(frame, pts[i - 1], pts[i], (255, 50, 50), thickness)

        # ---------------------------------------------------------
        # 7. 제스처 판단 엔진 (흔들기 vs 스냅 구분 + 주워들기 방지)
        # ---------------------------------------------------------
        # 스티커를 집어들거나 새로 감지된 직후(15프레임 이내)에는 제스처 판단을 잠금(Lockout)
        is_startup_lock = tracking_active_frames <= 15
        
        if len(pts) >= 6 and cooldown_counter == 0 and not is_startup_lock:
            
            # --- [A] 흔들기(SHAKE) 제스처 판단 (방향 전환 횟수 계산) ---
            dx_list = []
            for i in range(1, len(pts)):
                diff = pts[i-1][0] - pts[i][0]
                dx_list.append(diff)
            
            # 미세 떨림 필터링한 의미 있는 가로 방향 이동 성분 추출
            sig_moves = [dx for dx in dx_list if abs(dx) > 6]
            
            direction_reversals = 0
            if len(sig_moves) >= 4:
                current_sign = 1 if sig_moves[0] > 0 else -1
                for val in sig_moves[1:]:
                    sign = 1 if val > 0 else -1
                    if sign != current_sign:
                        direction_reversals += 1
                        current_sign = sign
            
            # 궤적의 전체 이동 경로 거리 계산
            total_path_dist = 0.0
            for i in range(1, len(pts)):
                total_path_dist += np.sqrt((pts[i-1][0] - pts[i][0])**2 + (pts[i-1][1] - pts[i][1])**2)
            
            # 흔들기 조건: 가로 방향 전환이 3회 이상 발생하고 누적 거리가 충분히 길 때
            if direction_reversals >= 3 and total_path_dist > 220:
                active_gesture = "SHAKE (HOME)"
                cooldown_counter = 25
                gesture_display_timer = 25
                pts.clear()
                
                # 앱 실행 상태라면 앱 종료 후 홈 화면으로, 홈 화면이라면 채널로, 채널이라면 홈 화면으로 전환
                if is_app_running:
                    is_app_running = False
                    is_home_mode = True
                else:
                    is_home_mode = not is_home_mode
                
            else:
                # --- [B] 스냅(SNAP) 제스처 판단 (직선성 검증 필터 적용) ---
                curr_pos = pts[0]
                past_pos = pts[SNAP_FRAME_WINDOW - 1]
                
                net_dx = curr_pos[0] - past_pos[0]
                net_dy = curr_pos[1] - past_pos[1]
                net_dist = np.sqrt(net_dx**2 + net_dy**2)
                
                # 스냅 판단 창 내의 누적 이동 경로 거리
                snap_window_path = 0.0
                for i in range(1, SNAP_FRAME_WINDOW):
                    snap_window_path += np.sqrt((pts[i-1][0] - pts[i][0])**2 + (pts[i-1][1] - pts[i][1])**2)
                
                # 직선 비율 (최단 변위 / 실제 궤적 길이)
                linear_ratio = net_dist / snap_window_path if snap_window_path > 0 else 0
                
                # 스냅은 곡률이 적고 직선성(직선비율 0.82 이상)이 우수해야 함
                if linear_ratio > 0.82:
                    abs_dx = abs(net_dx)
                    abs_dy = abs(net_dy)
                    
                    # 1. 수평 스냅 (Left/Right)
                    if abs_dx > SNAP_DIST_THRESHOLD_X and abs_dx > 1.8 * abs_dy:
                        if net_dx > 0:
                            active_gesture = "RIGHT SNAP"
                            if is_app_running:
                                # 앱 실행 중에는 제스처가 발생하면 앱 강제 종료 및 홈 화면 복귀
                                is_app_running = False
                            elif is_home_mode:
                                # 홈 화면 앱 선택 우측 이동
                                selected_app_idx = (selected_app_idx + 1) % len(apps)
                            else:
                                # 일반 TV 다음 채널 변경
                                current_channel_idx = (current_channel_idx + 1) % len(CHANNELS)
                        else:
                            active_gesture = "LEFT SNAP"
                            if is_app_running:
                                is_app_running = False
                            elif is_home_mode:
                                # 홈 화면 앱 선택 좌측 이동
                                selected_app_idx = (selected_app_idx - 1) % len(apps)
                            else:
                                # 일반 TV 이전 채널 변경
                                current_channel_idx = (current_channel_idx - 1) % len(CHANNELS)
                        
                        cooldown_counter = 20
                        gesture_display_timer = 25
                        pts.clear()
                        
                    # 2. 수직 스냅 (Up/Down)
                    elif abs_dy > SNAP_DIST_THRESHOLD_Y and abs_dy > 1.8 * abs_dx:
                        if net_dy < 0:  # 위로 휙
                            active_gesture = "UP SNAP"
                            if is_app_running:
                                is_app_running = False
                            elif is_home_mode:
                                # 홈 화면에서 위로 스냅 시 포커스된 앱을 실행!
                                is_app_running = True
                                running_app_name = apps[selected_app_idx]
                            else:
                                volume = min(100, volume + 10)
                        else:           # 아래로 휙
                            active_gesture = "DOWN SNAP"
                            if is_app_running:
                                is_app_running = False
                            elif is_home_mode:
                                # 홈 화면에서 아래로 스냅 시 스마트 허브 끄고 일반 TV로 복귀
                                is_home_mode = False
                            else:
                                volume = max(0, volume - 10)
                        
                        cooldown_counter = 20
                        gesture_display_timer = 25
                        pts.clear()

        # ---------------------------------------------------------
        # 8. 가상 스마트 TV 화면 그리기 (오른쪽 640x480 캔버스)
        # ---------------------------------------------------------
        tv_canvas = np.zeros((480, 640, 3), dtype=np.uint8)
        tv_canvas[:] = (36, 24, 18) # TV 기본 배경
        
        cv2.rectangle(tv_canvas, (10, 10), (630, 470), (100, 100, 100), 3) # 은색 베젤
        cv2.rectangle(tv_canvas, (20, 20), (620, 410), (10, 10, 10), -1) # 이너 스크린

        if tv_power:
            # 8.1 가상 앱 실행 화면 출력
            if is_app_running:
                screen_sub = tv_canvas[25:405, 25:615]
                sh, sw, _ = screen_sub.shape
                
                if running_app_name == "Netflix":
                    screen_sub[:] = (20, 20, 180) # 넷플릭스 레드 테마 BGR
                    # 'N' 로고 그리기
                    cv2.putText(screen_sub, "N", (sw//2 - 40, sh//2 - 20), 
                                cv2.FONT_HERSHEY_TRIPLEX, 5.0, (255, 255, 255), 8, cv2.LINE_AA)
                    cv2.putText(screen_sub, "NETFLIX ORIGINAL STREAMING", (sw//2 - 170, sh//2 + 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (220, 220, 220), 2)
                    
                elif running_app_name == "YouTube":
                    screen_sub[:] = (30, 30, 30) # 다크 테마 BGR
                    # 유튜브 재생 버튼 심볼
                    pts_poly = np.array([[sw//2-30, sh//2-40], [sw//2-30, sh//2+40], [sw//2+40, sh//2]], np.int32)
                    cv2.fillPoly(screen_sub, [pts_poly], (50, 50, 240)) # 빨간 재생 삼각버튼
                    cv2.putText(screen_sub, "YouTube Live Player", (sw//2 - 110, sh//2 + 65), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                    
                elif running_app_name == "Disney+":
                    screen_sub[:] = (120, 60, 10) # 디즈니 딥블루 BGR
                    cv2.ellipse(screen_sub, (sw//2, sh//2 - 20), (100, 100), 0, 180, 360, (255, 255, 255), 3)
                    cv2.putText(screen_sub, "DISNEY+", (sw//2 - 90, sh//2 + 30), 
                                cv2.FONT_HERSHEY_TRIPLEX, 1.5, (0, 215, 255), 3)
                    cv2.putText(screen_sub, "Start Streaming Magic", (sw//2 - 100, sh//2 + 65), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
                    
                else: # Settings
                    screen_sub[:] = (80, 80, 80) # 회색 테마 BGR
                    # 톱니바퀴 모사
                    cv2.circle(screen_sub, (sw//2, sh//2 - 30), 40, (120, 120, 120), -1)
                    cv2.circle(screen_sub, (sw//2, sh//2 - 30), 15, (80, 80, 80), -1)
                    cv2.putText(screen_sub, "SYSTEM SETTINGS", (sw//2 - 110, sh//2 + 40), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 앱 실행 중 안내 라벨
                cv2.rectangle(tv_canvas, (20, 20), (620, 70), (0, 0, 0), -1)
                cv2.putText(tv_canvas, f"App Running: {running_app_name}", (35, 52), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                cv2.putText(tv_canvas, "Shake / Swipe to Exit", (430, 52), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
                
            # 8.2 스마트 TV 홈 화면 (스마트 허브 대시보드)
            elif is_home_mode:
                # 대시보드 뒷배경 그라데이션 시뮬레이션
                screen_sub = tv_canvas[25:405, 25:615]
                sh, sw, _ = screen_sub.shape
                screen_sub[:] = (60, 45, 30) # 짙은 회자색 BGR
                
                # 타이틀 바
                cv2.putText(screen_sub, "SMART TV HUB - HOME", (20, 45), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                cv2.putText(screen_sub, "Swipe Left/Right to browse, Swipe UP to open, Swipe DOWN to close", (20, 75), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
                
                # 4가지 앱 카드(Netflix, YouTube, Disney+, Settings) 가로 배치
                card_w = 120
                card_h = 160
                gap = 20
                start_x = (sw - (card_w * 4 + gap * 3)) // 2
                card_y = 130
                
                for idx, app_name in enumerate(apps):
                    x1 = start_x + idx * (card_w + gap)
                    y1 = card_y
                    x2 = x1 + card_w
                    y2 = y1 + card_h
                    
                    # 현재 포커스(선택)된 앱 카드 강조 렌더링
                    if idx == selected_app_idx:
                        # 약간 큰 테두리 확장 및 화려한 네온 그린(0,255,100) 백그라운드 빛 효과
                        cv2.rectangle(screen_sub, (x1-6, y1-6), (x2+6, y2+6), (0, 255, 100), 3)
                        card_bg = (40, 40, 40)
                    else:
                        cv2.rectangle(screen_sub, (x1, y1), (x2, y2), (100, 100, 100), 1)
                        card_bg = (20, 20, 20)
                        
                    # 카드 내부 드로잉
                    cv2.rectangle(screen_sub, (x1, y1), (x2, y2), card_bg, -1)
                    
                    # 앱 로고 아이콘 단순 드로잉
                    icon_cy = y1 + 60
                    icon_cx = x1 + card_w // 2
                    if app_name == "Netflix":
                        cv2.putText(screen_sub, "N", (icon_cx - 15, icon_cy + 15), cv2.FONT_HERSHEY_TRIPLEX, 1.5, (0, 0, 255), 3)
                    elif app_name == "YouTube":
                        cv2.rectangle(screen_sub, (icon_cx-25, icon_cy-15), (icon_cx+25, icon_cy+15), (0, 0, 255), -1)
                        # 세모
                        pts_tri = np.array([[icon_cx-6, icon_cy-10], [icon_cx-6, icon_cy+10], [icon_cx+8, icon_cy]], np.int32)
                        cv2.fillPoly(screen_sub, [pts_tri], (255, 255, 255))
                    elif app_name == "Disney+":
                        cv2.circle(screen_sub, (icon_cx, icon_cy), 22, (255, 120, 10), 2)
                        cv2.putText(screen_sub, "D+", (icon_cx-17, icon_cy+7), cv2.FONT_HERSHEY_TRIPLEX, 0.6, (0, 255, 255), 1)
                    else: # Settings
                        cv2.circle(screen_sub, (icon_cx, icon_cy), 20, (150, 150, 150), 3)
                        cv2.circle(screen_sub, (icon_cx, icon_cy), 6, (80, 80, 80), -1)
                        
                    # 앱 텍스트 명칭 출력
                    cv2.putText(screen_sub, app_name, (x1 + 10, y2 - 20), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
            # 8.3 일반 TV 방송 재생 채널 화면
            else:
                ch = CHANNELS[current_channel_idx]
                screen_sub = tv_canvas[25:405, 25:615]
                sh, sw, _ = screen_sub.shape
                
                # 채널 테마별 동적 무빙 애니메이션
                if ch["theme"] == "news":
                    cv2.rectangle(screen_sub, (0, 0), (sw, sh), (60, 20, 10), -1)
                    cv2.ellipse(screen_sub, (sw//2, sh//2), (180, 120), 0, 0, 360, (120, 60, 30), 2)
                    cv2.ellipse(screen_sub, (sw//2, sh//2), (220, 60), 15, 0, 360, (150, 80, 40), 1)
                    cv2.rectangle(screen_sub, (0, sh-60), (sw, sh), (30, 30, 200), -1)
                    cv2.putText(screen_sub, "LIVE BROADCAST - STICKER CONTROLLER DEMO", (20, sh-20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                elif ch["theme"] == "music":
                    cv2.rectangle(screen_sub, (0, 0), (sw, sh), (20, 10, 30), -1)
                    r1 = int((frame_count * 2) % 150) + 10
                    r2 = int((frame_count * 3) % 200) + 10
                    cv2.circle(screen_sub, (sw//3, sh//2), r1, (255, 50, 180), 2)
                    cv2.circle(screen_sub, (2*sw//3, sh//2), r2, (50, 255, 200), 2)
                    t_val = (frame_count % 40) - 20
                    cv2.line(screen_sub, (0, 0), (sw//2 + t_val * 5, sh), (0, 200, 255), 1)
                    cv2.line(screen_sub, (sw, 0), (sw//2 - t_val * 5, sh), (255, 0, 255), 1)
                    
                elif ch["theme"] == "variety":
                    cv2.rectangle(screen_sub, (0, 0), (sw, sh), (10, 50, 60), -1)
                    for idx, r_div in enumerate([4, 6, 8, 12]):
                        bx = int((frame_count * (idx + 1) * 3) % sw)
                        by = int(((np.sin(frame_count / 10.0 + idx) + 1.0) * 100) + 100)
                        cv2.circle(screen_sub, (bx, by), 15 + idx * 5, (80, 200, 230), -1)
                    cv2.putText(screen_sub, "LOL!", (sw//2 - 50, sh//2),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 220, 255), 3)
                    
                elif ch["theme"] == "inkigayo":
                    cv2.rectangle(screen_sub, (0, 0), (sw, sh), (40, 20, 10), -1)
                    offset = (frame_count * 4) % 60
                    for x_line in range(-100, sw + 100, 60):
                        cv2.line(screen_sub, (x_line + offset, 0), (x_line - 100 + offset, sh), (180, 100, 50), 2)
                    
                elif ch["theme"] == "ytn":
                    cv2.rectangle(screen_sub, (0, 0), (sw, sh), (15, 15, 35), -1)
                    cv2.circle(screen_sub, (sw//2, sh//2 - 20), 60, (200, 50, 50), -1)
                    cv2.putText(screen_sub, "YTN", (sw//2 - 35, sh//2 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 3)
                    cv2.rectangle(screen_sub, (0, sh-40), (sw, sh), (50, 50, 50), -1)
                    cv2.putText(screen_sub, "BREAKING: GESTURE CONTROL TECHNOLOGY PROPOSED", (10, sh-15),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (100, 255, 255), 1)

            # --- TV 기본 상태 정보 오버레이 (채널 모드일 때만 활성화) ---
            if not is_home_mode and not is_app_running:
                ch = CHANNELS[current_channel_idx]
                cv2.rectangle(tv_canvas, (20, 20), (620, 80), (0, 0, 0), -1)
                cv2.putText(tv_canvas, f"CH {ch['num']}", (35, 60), 
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3)
                cv2.putText(tv_canvas, f"|  {ch['name']}", (140, 58), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(tv_canvas, f"ON AIR: {ch['show']}", (280, 58), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

            # --- TV 볼륨 게이지 바 (앱이 구동 중이지 않을 때만 상시 표시) ---
            if not is_app_running:
                vol_x_start = 50
                vol_y = 370
                vol_width = 300
                cv2.putText(tv_canvas, "VOL", (vol_x_start - 30, vol_y + 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
                cv2.rectangle(tv_canvas, (vol_x_start, vol_y), (vol_x_start + vol_width, vol_y + 12), (50, 50, 50), -1)
                filled_w = int((volume / 100.0) * vol_width)
                if volume > 0:
                    cv2.rectangle(tv_canvas, (vol_x_start, vol_y), (vol_x_start + filled_w, vol_y + 12), (0, 255, 100), -1)
                cv2.putText(tv_canvas, f"{volume}", (vol_x_start + vol_width + 10, vol_y + 11), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 100), 1)

            # --- 제스처 감지 팝업 알림창 렌더링 ---
            if active_gesture:
                popup_y = 200
                
                # SHAKE 제스처는 노란색으로 강조
                if "SHAKE" in active_gesture:
                    cv2.rectangle(tv_canvas, (120, popup_y - 40), (520, popup_y + 30), (0, 80, 80), -1)
                    cv2.rectangle(tv_canvas, (120, popup_y - 40), (520, popup_y + 30), (0, 200, 255), 2)
                    cv2.putText(tv_canvas, f"GESTURE: {active_gesture}", (140, popup_y - 12), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(tv_canvas, "Toggle Home Smart Hub Mode", (140, popup_y + 18), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                else:
                    cv2.rectangle(tv_canvas, (120, popup_y - 40), (520, popup_y + 30), (0, 100, 0), -1)
                    cv2.rectangle(tv_canvas, (120, popup_y - 40), (520, popup_y + 30), (0, 255, 0), 2)
                    cv2.putText(tv_canvas, f"GESTURE: {active_gesture}", (140, popup_y - 12), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    action_text = ""
                    if is_app_running:
                        action_text = "Launching Selected App..."
                    elif is_home_mode:
                        if "UP" in active_gesture:
                            action_text = "Select & Open App"
                        elif "DOWN" in active_gesture:
                            action_text = "Exit Smart Hub"
                        else:
                            action_text = f"Move App Focus to {apps[selected_app_idx]}"
                    else:
                        if "LEFT" in active_gesture:
                            action_text = "<< Channel Down"
                        elif "RIGHT" in active_gesture:
                            action_text = ">> Channel Up"
                        elif "UP" in active_gesture:
                            action_text = "++ Volume Up"
                        elif "DOWN" in active_gesture:
                            action_text = "-- Volume Down"
                        
                    cv2.putText(tv_canvas, action_text, (140, popup_y + 18), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            cv2.putText(tv_canvas, "TV POWER OFF", (220, 220), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 150), 2)

        # ---------------------------------------------------------
        # 9. 하단 상태 표시바 (도움말 및 안내 텍스트)
        # ---------------------------------------------------------
        cv2.rectangle(frame, (0, 440), (640, 480), (30, 30, 30), -1)
        
        # 스타트업 락아웃 중일 때 문구 변경
        if is_startup_lock and sticker_tracked:
            status_txt = f"TRACK: CALIBRATING ({tracking_active_frames}/15) | MODE: {'MOUSE' if use_mouse_sim else 'CAMERA'}"
            track_color = (0, 150, 255)
        else:
            status_txt = f"TRACK: {'OK' if sticker_tracked else 'LOST'} | MODE: {'MOUSE' if use_mouse_sim else 'CAMERA'} (m:Toggle)"
            track_color = (0, 255, 0) if sticker_tracked else (0, 0, 255)
            
        cv2.putText(frame, status_txt, (15, 465), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, track_color, 1)

        cv2.rectangle(tv_canvas, (0, 420), (640, 480), (20, 20, 20), -1)
        
        # 홈모드 여부에 따라 가이드 내용 동적 변경
        if is_app_running:
            help_txt = "Shake / Swipe: Exit App  |  [ESC]: Exit System"
        elif is_home_mode:
            help_txt = "Snap L/R: Browse App  |  UP: Open App  |  DOWN/Shake: Close Hub"
        else:
            help_txt = "Snap L/R: CH Up/Down  |  U/D: Vol  |  Shake: Open Smart Hub"
            
        cv2.putText(tv_canvas, help_txt, (20, 455), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        # ---------------------------------------------------------
        # 10. 화면 병합 및 출력
        # ---------------------------------------------------------
        combined_win = np.hstack((frame, tv_canvas))
        cv2.imshow(win_name, combined_win)

        key = cv2.waitKey(20) & 0xFF
        
        if key == 27:  # ESC
            print("[INFO] ESC 키가 감지되어 프로그램을 종료합니다.")
            break
        elif key == ord('c') or key == ord('C'):
            pts.clear()
            print("[INFO] 궤적이 초기화되었습니다.")
        elif key == ord('m') or key == ord('M'):
            if webcam_available:
                use_mouse_sim = not use_mouse_sim
                pts.clear()
                tracking_active_frames = 0
                print(f"[INFO] 조작 모드 변경: {'마우스 시뮬레이션' if use_mouse_sim else '실시간 카메라'}")
            else:
                print("[WARNING] 카메라를 사용할 수 없어 마우스 모드로 유지됩니다.")

    if cap.isOpened():
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
