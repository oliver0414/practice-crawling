from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
import csv

# ===== 크롬 드라이버 설정 =====
options = Options()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

driver = webdriver.Chrome(options=options)

# ===== URL 설정 =====
base_url = "https://padm.kangwon.ac.kr"
list_url = f"{base_url}/padm/life/notice-department.do"

# ===== HTML 태그 제거 및 표 처리 =====
def clean_html_keep_table(raw_html):
    soup = BeautifulSoup(raw_html, 'html.parser')

    output_text = ''

    # 🔥 1. 테이블 먼저 추출
    tables = soup.find_all('table')
    for table in tables:
        table_text = extract_table_text(table)
        if table_text.strip():
            output_text += table_text + '\n'
        table.decompose()  # ✅ 테이블 제거 (중복 방지)

    # 🔥 2. 남은 본문 (p, div 등) 추출
    for elem in soup.find_all(['p', 'div']):
        text = elem.get_text(strip=True)
        if text:
            output_text += text + '\n'

    return output_text.strip()



def extract_table_text(table):
    rows = table.find_all('tr')
    table_text = ''
    for row in rows:
        cols = row.find_all(['td', 'th'])
        valid_cols = [col.get_text(strip=True) for col in cols if col.get_text(strip=True)]
        if valid_cols:
            row_text = ' | '.join(valid_cols)
            table_text += row_text + '\n'
    return table_text


# ===== 공지 리스트 크롤링 =====
def crawl_notice_list(offset=0):
    driver.get(f"{list_url}?article.offset={offset}")
    time.sleep(2)

    notices = []
    rows = driver.find_elements(By.CSS_SELECTOR, 'td.b-td-left.b-td-title')

    for row in rows:
        try:
            link_tag = row.find_element(By.CSS_SELECTOR, 'div.b-title-box a')
            title = link_tag.text.strip()
            href = link_tag.get_attribute('href')
            detail_url = base_url + "/padm/life/notice-department.do" + href[href.find('?'):]
            notices.append({'title': title, 'url': detail_url})
        except Exception as e:
            print("[!] 리스트 항목 파싱 실패:", e)
            continue

    return notices

# ===== 공지 본문 크롤링 (본문 + 표 처리) =====
def crawl_notice_detail(url):
    driver.get(url)

    selector_candidates = [
        'div.b-content-box div.fr-view',
        'div.b-content-box'
    ]

    for selector in selector_candidates:
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            element = driver.find_element(By.CSS_SELECTOR, selector)
            content_html = element.get_attribute('innerHTML')
            content_text = clean_html_keep_table(content_html)
            if content_text.strip():
                return content_text
        except:
            continue

    return "(본문 없음)"

# ===== 메인 실행 =====
if __name__ == "__main__":
    all_notices = []

    # ✅ 여러 페이지 크롤링 (예시: 1~2페이지만)
    for offset in range(0, 20, 10):  # 10개 단위로: 0, 10, 20, ...
        notices = crawl_notice_list(offset=offset)

        for notice in notices:
            title = notice['title']
            url = notice['url']
            content = crawl_notice_detail(url)

            all_notices.append({'제목': title, '본문': content})

            print("==== 제목 ====")
            print('● '+title)
            print("==== 본문 ====")
            print(content)
            print("\n\n")

    driver.quit()
