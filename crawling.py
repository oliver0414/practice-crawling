from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re

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

    tables = soup.find_all('table')
    for table in tables:
        table_text = extract_table_text(table)
        if table_text.strip():
            output_text += table_text + '\n'
        table.decompose()

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

# ===== 공지 본문, 작성일, 파일링크 크롤링 =====
def crawl_notice_detail(url):
    driver.get(url)

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # 본문
    content_area = soup.select_one('div.b-content-box div.fr-view') or soup.select_one('div.b-content-box')
    if content_area:
        content_html = content_area.decode_contents()
        content_text = clean_html_keep_table(content_html)
    else:
        content_text = "(본문 없음)"

    # 작성일
    date_area = soup.select_one('div.b-etc-box li.b-date-box span:last-child')
    if date_area:
        written_date = date_area.text.strip()
    else:
        written_date = "(작성일 없음)"

    # 문서 파일 링크
    doc_links = []
    file_area = soup.select('div.b-file-box a')
    for file_tag in file_area:
        href = file_tag.get('href')
        filename = file_tag.text.strip()
        if href and (filename.endswith('.hwp') or filename.endswith('.pdf')):
            doc_links.append(base_url + "/padm/life/notice-department.do" + href[href.find('?'):])

    # 이미지 파일 링크
    img_links = []
    for file_tag in file_area:
        href = file_tag.get('href')
        filename = file_tag.text.strip()
        if href and (filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg')):
            img_links.append(base_url + "/padm/life/notice-department.do" + href[href.find('?'):])

    return content_text, written_date, doc_links, img_links

# ===== 메인 실행 =====
if __name__ == "__main__":
    all_notices = []

    for offset in range(0, 20, 10):
        notices = crawl_notice_list(offset=offset)

        for notice in notices:
            title = notice['title']
            url = notice['url']
            content, written_date, doc_links, img_links = crawl_notice_detail(url)

            all_notices.append({
                '제목': title,
                '작성일': written_date,
                '본문': content,
                '문서파일링크': doc_links,
                '이미지파일링크': img_links
            })

            print("==== 제목 ====")
            print(title)
            print("==== 작성일 ====")
            print(written_date)
            print("==== 본문 ====")
            print(content)
            print("==== 이미지파일 ====")
            print(img_links)
            print("==== 문서파일 ====")
            print(doc_links)
            print("\n\n")

    driver.quit()
