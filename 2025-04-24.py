from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import re
import time

# ===== 날짜 정규화 =====
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

def extract_event_dates(text):
    lines = text.splitlines()

    for line in lines:
        if any(kw in line for kw in ["일시", "일 시", "운영기간", "행사기간", "진행기간", "교육기간", "프로그램 기간"]):
            # 🔥 괄호 안 부가설명 제거
            line = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", "", line)  # (월), [정보] 등 제거
            line = re.sub(r"[〔〕]", "", line)  # 유니코드 괄호 제거

            # 🔥 날짜 구간 추출
            date_range_match = re.search(
                r"(20\d{2}[.년\s]*\d{1,2}[.월\s]*\d{1,2}[일]*)\s*[~∼－ー-]+\s*(\d{1,2}[.월\s]*\d{1,2}[일]*)",
                line
            )
            if date_range_match:
                start_raw = date_range_match.group(1)
                end_raw = date_range_match.group(2)
                start = normalize_to_iso(start_raw)
                if not re.search(r"20\d{2}", end_raw):
                    start_year = datetime.strptime(start, "%Y-%m-%d").year
                    end_raw = f"{start_year}년{end_raw}"
                end = normalize_to_iso(end_raw)
                if start and end:
                    return [start, end]

    # 🔁 fallback: 단일 날짜들 추출
    patterns = [
        r'20\d{2}[./-]\d{1,2}[./-]\d{1,2}',
        r'20\d{2}년\s?\d{1,2}월\s?\d{1,2}일',
        r'\d{1,2}월\s?\d{1,2}일',
        r'\d{1,2}[./]\d{1,2}'
    ]
    iso_dates = set()
    for line in lines:
        if "신청" in line or "접수" in line or "모집" in line:
            continue
        for pattern in patterns:
            for match in re.findall(pattern, line):
                normalized = normalize_to_iso(match)
                if normalized:
                    iso_dates.add(normalized)

    return sorted(iso_dates) if iso_dates else None





#===== 신청 마감일 추출 =======
def extract_deadline_date(text):
    lines = text.splitlines()
    for line in lines:
        if any(kw in line for kw in ["신청기간", "모집기간", "접수기간", "신청기한", "모집기한", "제출기한", "신청 마감", "접수 마감", "모집기간"]):
            matches = re.findall(r'(20\d{2}[./년\s]*\d{1,2}[./월\s]*\d{1,2}[일\s]*)|(\d{1,2}[./월\s]*\d{1,2}[일\s]*)', line)
            dates = []
            for full_match in matches:
                date_raw = full_match[0] if full_match[0] else full_match[1]
                normalized = normalize_to_iso(date_raw)
                if normalized:
                    dates.append(normalized)
            if dates:
                return max(dates)
    return None


# ===== 기타 필드 추출 =====
def clean_prefix(line: str) -> str:
    return re.sub(r"^[가-힣]\.|\d+[.)]|[-•○]\s*", "", line).strip()

def extract_target(text):
    keywords = ["참가대상", "모집대상", "지원자격", "대상자", "신청자격", "자격요건", "대상"]
    for kw in keywords:
        for line in text.splitlines():
            if kw in line:
                return clean_prefix(line.strip())
    return None

def extract_apply_method(text):
    keywords = ["신청방법", "지원방법", "접수방법", "참여신청", "신청 방법", "지원 방법", "교육 신청"]
    for kw in keywords:
        for line in text.splitlines():
            if kw in line:
                return clean_prefix(line.strip())
    return None

def extract_locations(text):
    text = re.sub(r'\d{4}[./년\s]*\d{1,2}[./월\s]*\d{1,2}[일\s]*', '', text)
    text = re.sub(r"\d{2}[./]\d{1,2}[./]\d{1,2}\.", "", text)

    postpositions = r"(에서|에|은|는|이|가|으로|로)\b"

    # ✅ "장 소:"처럼 띄어쓰기 있는 형태도 인식
    match = re.search(r"장\s*소\s*[:：]?\s*(.*)", text)
    if match:
        raw_loc = match.group(1).strip()
        raw_loc = re.split(r"[,.등]", raw_loc)[0].strip()
        if any(bad in raw_loc for bad in ["없음", "미정", "별도", "문의", "추후"]):
            return None
        return raw_loc

    # 백업: 패턴 기반 장소 추출
    patterns = [
        r"(미래도서관\s?[가-힣\w\s\(\)]+)",
        r"(공6|공5|공4|공3|공2|공1|경영|도서관|호관|공과대학|강의실|○○관|농1|농2|농3|BF\d)[\w\s\d호]*",
        r"(서울대학교)", r"(춘천\s?[가-힣\d]*)"
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            location = re.split(postpositions, match.group().strip())[0].strip()
            if any(bad in location for bad in ["없음", "미정", "별도", "문의", "추후"]):
                return None
            return location
    return None



    # 백업 패턴 기반 처리
    patterns = [
        r"(미래도서관\s?[가-힣\w\s\(\)]+)",
        r"(공6|공5|공4|공3|공2|공1|경영|도서관|호관|공과대학|강의실|○○관|농1|농2|농3|BF\d)[\w\s\d호]*",
        r"(서울대학교)", r"(춘천\s?[가-힣\d]*)"
    ]
    for p in patterns:
        match = re.search(p, text)
        if match:
            location = re.split(postpositions, match.group().strip())[0].strip()
            if any(bad in location for bad in ["없음", "미정", "별도", "문의", "추후"]):
                return None
            return location
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

# ===== 통합 정보 추출 함수 =====
def extract_info(title, content):
    full_text = f"{title}\n{content}"
    return {
        "제목": title,
        "날짜": extract_event_dates(full_text),
        "장소": extract_locations(full_text),
        "신청방법": extract_apply_method(full_text),
        "대상": extract_target(full_text),
        "신청마감일": extract_deadline_date(full_text),
        "카테고리": classify_category(full_text)
    }

# ===== 크롤링 실행 =====
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get("https://padm.kangwon.ac.kr/padm/life/notice-department.do")
time.sleep(2)

all_hrefs = set()
page_num = 1

while page_num <= 3:
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
    except:
        break

print(f"\n[+] 총 {len(all_hrefs)}개의 공지 링크 수집 완료.\n")

# ===== 공지 상세 추출 =====
i = 1
for url in all_hrefs:
    driver.get(url)
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "p.b-title-box span")))
        title = driver.find_element(By.CSS_SELECTOR, "p.b-title-box span").text.strip()

        try:
            content = driver.find_element(By.CSS_SELECTOR, "div.b-content-box div.fr-view").text.strip()
        except:
            continue

        if re.fullmatch(r"\[?공지\]?", title):
            continue

        info = extract_info(title, content)
        print(f"🔹 [{i}] {info['제목']}")
        print(f"📅 날짜: {info['날짜'][0]} ~ {info['날짜'][1]}" if info['날짜'] and len(info['날짜']) == 2 else f"📅 날짜: {info['날짜'][0]}" if info['날짜'] else "📅 날짜: 없음")
        print(f"📍 장소: {info['장소'] if info['장소'] else '없음'}")
        print(f"👤 대상: {info['대상'] if info['대상'] else '없음'}")
        print(f"📬 신청방법: {info['신청방법'] if info['신청방법'] else '없음'}")
        print(f"⏳ 신청마감일: {info['신청마감일'] if info['신청마감일'] else '없음'}")
        print(f"🏷️ 카테고리: {info['카테고리']}")
        print("-" * 60 + "\n")
        i += 1

    except Exception as e:
        print(f"[!] [{i}] 크롤링 실패: {e}")

driver.quit()
