from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# 크롬 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")
# options.add_argument("--headless")  # 원할 경우 숨김 모드 사용 가능

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# 공지사항 리스트 페이지 진입
driver.get("https://padm.kangwon.ac.kr/padm/life/notice-department.do")
time.sleep(2)

# 공지사항 링크 추출 (1페이지 기준)
notice_links = driver.find_elements(By.CSS_SELECTOR, "td.b-td-left.b-td-title a")
hrefs = [link.get_attribute("href") for link in notice_links if link.get_attribute("href")]

print(f"[+] 공지 {len(hrefs)}개를 수집했습니다.\n")

for i, url in enumerate(hrefs, 1):
    driver.get(url)

    try:
        # 제목이 렌더링될 때까지 대기
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "p.b-title-box span"))
        )

        title = driver.find_element(By.CSS_SELECTOR, "p.b-title-box span").text.strip()
        content = driver.find_element(By.CSS_SELECTOR, "div.b-content-box div.fr-view").text.strip()

        print(f"🔹 [{i}] {title}")
        print("-" * 60)
        print(content[:1000], "...\n")  # 본문 일부만 표시

    except Exception as e:
        print(f"[!] [{i}] 크롤링 실패: {e}")

driver.quit()
