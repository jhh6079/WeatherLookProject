from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import json

# WebDriver 설정
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

# URL 설정
url = "https://www.musinsa.com/snap/main/recommend"
driver.get(url)

# 스크롤 로드 함수
def load_more_content():
    """ 페이지 하단으로 스크롤하여 콘텐츠 로드 """
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)  # 로딩 대기

# 이미지 추출 및 출력
def get_image_urls():
    """ 현재 페이지의 모든 이미지 URL 추출 (광고 제외) """
    img_elements = driver.find_elements(By.CSS_SELECTOR, ".sc-6fd591d8-0 img")  # 이미지 CSS 선택자
    img_urls = []

    for img in img_elements:
        try:
            # 광고 요소 필터링: 'hpPCle.gtm' 클래스 포함 여부 확인
            img.find_element(By.XPATH, "./ancestor::div[contains(@class, 'hpPCle.gtm')]")
            # 부모 요소에 'hpPCle.gtm' 클래스가 있으면 광고로 간주하고 제외
            continue
        except Exception:
            # 부모 요소가 없거나 광고가 아닌 경우
            img_src = img.get_attribute("src")
            if img_src:  # 유효한 URL만 추가
                img_urls.append(img_src)

    return img_urls

# 초기 로딩 대기
time.sleep(2)

# 이미지 크롤링
img_list = []  # 이미지 URL을 리스트에 저장
scroll_limit = 5  # 스크롤 최대 횟수
current_scroll = 0

while current_scroll <= scroll_limit:
    # 현재 페이지의 이미지 수집
    new_img_urls = get_image_urls()
    for img_url in new_img_urls:
        # 중복 제거
        if img_url not in img_list:
            img_list.append(img_url)

    print(f"{current_scroll + 1}번째 스크롤에서 {len(new_img_urls)}개의 이미지 URL을 수집했습니다.")
    load_more_content()
    current_scroll += 1

# 딕셔너리 형태로 저장
result = {"images": img_list}

# JSON 파일로 저장
output_file = "image_urls.json"
with open(output_file, "w") as file:
    json.dump(result, file, indent=4)
print(f"이미지 URL이 '{output_file}' 파일에 저장되었습니다.")

# 브라우저 종료
driver.quit()