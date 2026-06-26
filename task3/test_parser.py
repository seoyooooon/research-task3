import re
from datetime import datetime

# 1. Title Cleaning Engine (Python equivalent)
def clean_content_title(raw_title):
    if not raw_title:
        return ''
    cleaned = raw_title.strip()

    # 1. Remove brackets content
    cleaned = re.sub(r'\[[^\]]*\]', '', cleaned)
    cleaned = re.sub(r'\([^)]*\)', '', cleaned)

    # 2. Split by typical delimiters
    if ':' in cleaned:
        cleaned = cleaned.split(':')[0]
    elif '-' in cleaned:
        cleaned = cleaned.split('-')[0]

    # 3. Remove episode, season indicators
    indicators = [
        r'\s시즌\s?\d+',
        r'\s\d+화',
        r'\s\d+부',
        r'\sseason\s?\d+',
        r'\sepisode\s?\d+',
        r'\spart\s?\d+'
    ]
    for pattern in indicators:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)

    return cleaned.strip()

# 2. Flexible Date Parser (Python equivalent)
def parse_date_flexible(date_str):
    if not date_str:
        return ''
    
    # Format YYYY-MM-DD
    yyyymmdd = re.match(r'^(\d{4})[-/.](1[0-2]|0?[1-9])[-/.](3[01]|[12]\d|0?[1-9])', date_str)
    if yyyymmdd:
        return f"{yyyymmdd.group(1)}-{yyyymmdd.group(2).zfill(2)}-{yyyymmdd.group(3).zfill(2)}"

    # Format M/D/YY or M/D/YYYY
    mdy = re.match(r'^(1[0-2]|0?[1-9])/(3[01]|[12]\d|0?[1-9])/(\d{2,4})', date_str)
    if mdy:
        year = mdy.group(3)
        if len(year) == 2:
            year = '20' + year
        return f"{year}-{mdy.group(1).zfill(2)}-{mdy.group(2).zfill(2)}"

    # General date parsing
    try:
        # Standard parsing with datetime
        dt = datetime.strptime(date_str.split()[0], '%Y-%m-%d')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass

    try:
        dt = datetime.strptime(date_str.split()[0], '%m/%d/%Y')
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass

    return ''

# --- Run Tests ---
print("--- Running Python Parser Unit Tests ---")

# Test 1: Title Cleaning
try:
    assert clean_content_title('오징어 게임: 시즌 1: 1화 무궁화 꽃이 피던 날') == '오징어 게임'
    assert clean_content_title('[넷플릭스] 기생충 (Parasite)') == '기생충'
    assert clean_content_title('귀멸의 칼날: 무한열차편: 2화') == '귀멸의 칼날'
    assert clean_content_title('인셉션') == '인셉션'
    assert clean_content_title('슬기로운 의사생활: 3화') == '슬기로운 의사생활'
    print("[OK] Title Cleaning Tests Passed!")
except AssertionError as e:
    print("[FAIL] Title Cleaning Tests Failed!")
    exit(1)

# Test 2: Date Parsing
try:
    assert parse_date_flexible('2026-06-01') == '2026-06-01'
    assert parse_date_flexible('2026/6/5') == '2026-06-05'
    assert parse_date_flexible('2026.06.10') == '2026-06-10'
    assert parse_date_flexible('6/17/26') == '2026-06-17'
    assert parse_date_flexible('06/17/2026 14:05:00') == '2026-06-17'
    print("[OK] Date Parsing Tests Passed!")
except AssertionError as e:
    print("[FAIL] Date Parsing Tests Failed!")
    exit(1)

print("--- All Python Unit Tests Passed! ---")
