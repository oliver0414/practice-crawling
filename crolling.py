from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time

# 셀레니움 드라이버 설정
options = Options()
options.add_argument('--headless')  # 브라우저 안 띄우기
options.add_argument('--disable-gpu')
service = Service(executable_path='chromedriver')  # 크롬드라이버 경로

driver = webdriver.Chrome(service=service, options=options)
url = "https://padm.kangwon.ac.kr/padm/life/notice-department.do"
driver.get(url)

time.sleep(2)  # 페이지 로딩 대기

# 공지사항 리스트 가져오기
notices = driver.find_elements(By.CSS_SELECTOR, "table.board-list tbody tr")

data = []

for notice in notices:
    title_elem = notice.find_element(By.CSS_SELECTOR, "td.title a")
    title = title_elem.text.strip()
    link = title_elem.get_attribute('href')
    data.append({
        'title': title,
        'link': link
    })

driver.quit()

# 결과 출력
for d in data:
    print(f"제목: {d['title']}")
    print(f"링크: {d['link']}")
    print("-" * 50)
