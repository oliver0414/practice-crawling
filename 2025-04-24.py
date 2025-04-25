from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import re
import time

# ===== 날짜 정규화 함수 =====
def normalize_to_iso(date_str):
    date_str = re.sub(r"\(.*?\)", "", date_str)
    date_str = date_str.replace("~", "").replace(" ", "")
    if re.search(r'\d{1,2}:\d{2}', date_str):
        return None
    formats = [
        "%Y년%m월%d일", "%Y.%m.%d", "%Y-%m-%d",
        "%m월%d일", "%m.%d"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if "년" not in fmt:
                dt = dt.replace(year=datetime.now().year)
            return dt.strftime("%Y-%m-%d")
        except:
            continue
    return None

# ===== 정보 추출 함수 =====
def extract_event_dates(text):
    patterns = [
        r'20\d{2}[./-]\d{1,2}[./-]\d{1,2}',
        r'20\d{2}년\s?\d{1,2}월\s?\d{1,2}일',
        r'\d{1,2}월\s?\d{1,2}일',
        r'\d{1,2}[./]\d{1,2}'
    ]
    lines = text.splitlines()
    iso_dates = set()

    for line in lines:
        if "신청" in line or "접수" in line:
            continue  # 신청 관련 날짜는 무시

        for pattern in patterns:
            matches = re.findall(pattern, line)
            for match in matches:
                normalized = normalize_to_iso(match)
                if normalized:
                    iso_dates.add(normalized)
    
    return sorted(iso_dates)

def clean_prefix(line: str) -> str:
    return re.sub(r"^[가-힣]\.|\d+[.)]|[-•]\s*", "", line).strip()

def extract_target(text):
    keywords = ["참가대상", "모집대상", "지원자격", "대상자", "신청자격","자격요견","대상"]
    for kw in keywords:
        for line in text.splitlines():
            if kw in line:
                return clean_prefix(line.strip())
    return None

def extract_locations(text):
    # 날짜 제거 (기존처럼)
    text = re.sub(r'\d{4}[./년\s]*\d{1,2}[./월\s]*\d{1,2}[일\s]*', '', text)
    text = re.sub(r"\d{2}[./]\d{1,2}[./]\d{1,2}\.", "", text)

    # 조사 제거 대상 패턴
    postpositions = r"(에서|에|은|는|이|가|으로|로)\b"

    # 장소 패턴 정의
    patterns = [
        r"(미래도서관\s?[가-힣\w\s\(\)]+)",
        r"(도서관|호관|공과대학|강의실|○○관|농1|농2|농3|BF\d)[\w\s\d호]*"
    ]

    for p in patterns:
        match = re.search(p, text)
        if match:
            location = match.group().strip()

            # 조사까지 포함된 경우 잘라냄
            location = re.split(postpositions, location)[0].strip()

            if any(bad in location for bad in ["없음", "미정", "별도", "추후"]):
                return None
            return location

    return None



def extract_apply_method(text):
    keywords = ["신청방법", "지원방법", "접수방법", "참여신청", "신청 방법", "지원 방법","교육 신청"]
    for kw in keywords:
        for line in text.splitlines():
            if kw in line:
                return clean_prefix(line.strip())
    return None

def classify_category(text):
    category_keywords = {
        "공모전": ["공모전", "경진대회", "아이디어", "콘테스트", "창업", "해커톤"],
        "대외활동": ["대외활동", "연수", "해외", "인턴", "봉사", "교류", "참가자 모집"],
        "비교과": ["비교과", "특강", "워크숍", "세미나", "강연", "소모임", "문해력", "역량"]
    }
    for category, keywords in category_keywords.items():
        if any(k in text for k in keywords):
            return category
    return "기타"

def extract_info(title, content):
    full_text = f"{title}\n{content}"
    return {
        "제목": title,
        "날짜": extract_event_dates(full_text),
        "장소": extract_locations(full_text),
        "신청방법": extract_apply_method(full_text),
        "대상": extract_target(full_text),
        "카테고리": classify_category(full_text)
    }

# ===== 크롬 설정 및 실행 =====
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://padm.kangwon.ac.kr/padm/life/notice-department.do")
time.sleep(2)

# ===== 전체 페이지에서 공지 링크 수집 =====
all_hrefs = set()
page_num = 1

while page_num <= 3:
    print(f"[+] {page_num}페이지 링크 수집 중...")
    WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "td.b-td-left.b-td-title a")))
    notice_links = driver.find_elements(By.CSS_SELECTOR, "td.b-td-left.b-td-title a")
    hrefs = [link.get_attribute("href") for link in notice_links if link.get_attribute("href")]
    all_hrefs.update(hrefs)

    try:
        next_page = driver.find_element(By.XPATH, f'//a[contains(@href, "goPage({page_num + 1}") or text()="{page_num + 1}"]')
        next_page.click()
        WebDriverWait(driver, 10).until(lambda d: str(page_num + 1) in d.page_source)
        time.sleep(1)
        page_num += 1
    except Exception as e:
        print(f"[!] 다음 페이지 없음 또는 종료: {e}")
        break

print(f"\n[+] 총 {len(all_hrefs)}개의 공지 링크를 수집했습니다.\n")

# ===== 공지 세부 정보 수집 =====
i = 1
for url in all_hrefs:
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.b-title-box span"))
        )
        title = driver.find_element(By.CSS_SELECTOR, "p.b-title-box span").text.strip()

        # 본문이 존재하지 않으면 건너뜀
        try:
            content = driver.find_element(By.CSS_SELECTOR, "div.b-content-box div.fr-view").text.strip()
        except:
            print(f"[!] [{i}] 본문 없음: {title} → 건너뜁니다.\n")
            continue

        # 이후 정보 추출
        info = extract_info(title, content)

        # 공지 제목이 "[공지]" 혹은 "공지"일 경우 제외
        if re.fullmatch(r"\[?공지\]?", title):
            continue

        print(f"🔹 [{i}] {info['제목']}")
        # 이하 생략...


        if info['날짜']:
            if len(info['날짜']) == 1:
                print(f"📅 날짜: {info['날짜'][0]}")
            else:
                print(f"📅 날짜: {min(info['날짜'])} ~ {max(info['날짜'])}")
        else:
            print("📅 날짜: 없음")

        print(f"📍 장소: {info['장소'] if info['장소'] else '없음'}")
        print(f"👤 대상: {info['대상'] if info['대상'] else '없음'}")
        print(f"📬 신청방법: {info['신청방법'] if info['신청방법'] else '없음'}")
        print(f"🏷️ 카테고리: {info['카테고리']}")
        print("-" * 60 + "\n")
        i += 1

    except Exception as e:
        print(f"[!] [{i}] 크롤링 실패: {e}")


driver.quit()
