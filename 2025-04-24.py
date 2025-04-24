from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import time

# ===== 정보 추출 함수 =====

def extract_dates(text):
    patterns = [
        r'\d{4}[./]\d{1,2}[./]\d{1,2}',         # 2025.04.30
        r'\d{1,2}월\s?\d{1,2}일',               # 4월 30일
        r'\d{4}년\s?\d{1,2}월\s?\d{1,2}일',     # 2025년 4월 30일
        r'\d{1,2}\.\d{1,2}',                    # 4.30
        r'\d{1,2}:\d{2}~\d{1,2}:\d{2}'          # 시간대
    ]
    results = []
    for p in patterns:
        results += re.findall(p, text)
    return list(set(results))

def extract_locations(text):
    location_patterns = [
        r'(장소|위치|강의장소|행사장소)[\s:：]*([^\n\(\)]+)',
        r'장소[^\n]{0,15}?\s([\w\s·\-\(\)BF]+관[\w\s\d호]*)'
    ]
    for pattern in location_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(2).strip()
    return None

def extract_apply_period(text):
    match = re.search(r'(\d{4}[./]\d{1,2}[./]\d{1,2})\s?[~\-]\s?(\d{4}[./]\d{1,2}[./]\d{1,2})', text)
    if match:
        return match.groups()
    match = re.search(r'(\d{1,2}\.\s?\d{1,2}\.\([가-힣]+\).*\d{2}:\d{2})\s?[~\-]\s?(\d{1,2}\.\s?\d{1,2}\.\([가-힣]+\).*\d{2}:\d{2})', text)
    if match:
        return match.groups()
    return None

def extract_info(title, content):
    full_text = f"{title}\n{content}"
    return {
        "제목": title,
        "날짜": extract_dates(full_text),
        "장소": extract_locations(full_text),
        "신청기간": extract_apply_period(full_text)
    }

# ===== 크롬 설정 및 크롤링 =====

options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

driver.get("https://padm.kangwon.ac.kr/padm/life/notice-department.do")
time.sleep(2)

notice_links = driver.find_elements(By.CSS_SELECTOR, "td.b-td-left.b-td-title a")
hrefs = [link.get_attribute("href") for link in notice_links if link.get_attribute("href")]

print(f"[+] 공지 {len(hrefs)}개를 수집했습니다.\n")

for i, url in enumerate(hrefs, 1):
    driver.get(url)

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.b-title-box span"))
        )
        title = driver.find_element(By.CSS_SELECTOR, "p.b-title-box span").text.strip()
        content = driver.find_element(By.CSS_SELECTOR, "div.b-content-box div.fr-view").text.strip()

        info = extract_info(title, content)

        print(f"🔹 [{i}] {info['제목']}")
        print(f"📅 날짜: {info['날짜']}")
        print(f"📍 장소: {info['장소']}")
        print(f"📝 신청기간: {info['신청기간']}")
        print("-" * 60 + "\n")

    except Exception as e:
        print(f"[!] [{i}] 크롤링 실패: {e}")

driver.quit()
