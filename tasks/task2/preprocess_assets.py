import cv2
import numpy as np
import os

def preprocess_glasses(img_path, output_path, threshold=245):
    """
    흰색 배경을 감지하여 정교하게 제거(누끼 처리)하고, 무의미한 빈 여백을 
    자동 크롭한 뒤 알파 채널(투명도)을 갖춘 PNG 이미지로 변환합니다.
    """
    # 이미지 읽기 (BGR)
    img = cv2.imread(img_path)
    if img is None:
        print(f"Error: {img_path} 파일을 읽을 수 없습니다.")
        return False
    
    # B, G, R 채널 분리 및 흰색 배경 마스크 검출
    b, g, r = cv2.split(img)
    white_mask = (b > threshold) & (g > threshold) & (r > threshold)
    
    # 알파 마스크 생성 (배경 영역 = 0 [투명], 안경 영역 = 255 [불투명])
    alpha_mask = np.ones(white_mask.shape, dtype=np.uint8) * 255
    alpha_mask[white_mask] = 0
    
    # [정밀 누끼 고도화] 침식(Erosion) 연산 적용
    # 3x3 타원형 커널로 1회 침식을 수행하여 안경 외각 경계선에 묻어있는 미세한 흰색 띠(Halo) 노이즈를 깎아냅니다.
    kernel_erode = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    alpha_mask = cv2.erode(alpha_mask, kernel_erode, iterations=1)
    
    # 실제 안경 영역(알파 > 0)의 경계 상자를 추출하여 무의미한 상하좌우 투명 여백 크롭
    pts = np.argwhere(alpha_mask > 0)
    if pts.size > 0:
        y_min, x_min = pts.min(axis=0)
        y_max, x_max = pts.max(axis=0)
        
        # 가장자리 손실 방지를 위한 3픽셀 크기의 마진 설정
        margin = 3
        h_orig, w_orig = alpha_mask.shape
        y_min = max(0, y_min - margin)
        y_max = min(h_orig - 1, y_max + margin)
        x_min = max(0, x_min - margin)
        x_max = min(w_orig - 1, x_max + margin)
        
        # 크롭 영역 슬라이싱 적용
        b = b[y_min:y_max+1, x_min:x_max+1]
        g = g[y_min:y_max+1, x_min:x_max+1]
        r = r[y_min:y_max+1, x_min:x_max+1]
        alpha_mask = alpha_mask[y_min:y_max+1, x_min:x_max+1]
    
    # 경계선을 조금 더 부드럽게 만들기 위해 가우시안 블러 및 필터링 수행
    alpha_mask = cv2.GaussianBlur(alpha_mask, (3, 3), 0)
    
    # BGRA 이미지로 병합
    rgba = cv2.merge([b, g, r, alpha_mask])
    
    # 결과 저장
    cv2.imwrite(output_path, rgba)
    print(f"전처리 완료 (정밀 누끼 & 크롭 적용): {img_path} -> {output_path} (크기: {rgba.shape[1]}x{rgba.shape[0]})")
    return True

def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(current_dir, "assets")
    
    glasses_configs = [
        ("raw_horn_rimmed.png", "horn_rimmed.png", 248),
        ("raw_metal_round.png", "metal_round.png", 245),
        ("raw_red_sunglasses.png", "red_sunglasses.png", 248)
    ]
    
    print("[INFO] 안경 이미지 에셋 투명화 및 정밀 누끼 전처리를 시작합니다...")
    for raw_name, out_name, thresh in glasses_configs:
        raw_path = os.path.join(assets_dir, raw_name)
        out_path = os.path.join(assets_dir, out_name)
        
        if os.path.exists(raw_path):
            preprocess_glasses(raw_path, out_path, thresh)
        else:
            print(f"[WARNING] 파일을 찾을 수 없습니다: {raw_path}")
    print("[INFO] 전처리가 완료되었습니다.")

if __name__ == "__main__":
    main()
