from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

# 실행 시간 측정을 위한 시작 시간 기록
start_time = time.time()

# Selenium WebDriver 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")  # 필요시 주석 처리 (headless 모드 비활성화)
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# WebDriver 초기화
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Musinsa 페이지 URL
url = "https://www.musinsa.com/main/musinsa/ranking?skip_bf=Y&storeCode=musinsa&sectionId=199&categoryCode=001000&gf=A"
driver.get(url)

# 링크 추출 범위 설정
start_div = 2
end_div = 35
results = []

for parent_index in range(start_div, end_div + 1):
    for child_index in range(1, 4):  # div:nth-child(1), div:nth-child(2), div:nth-child(3)
        try:
            # 링크 XPath
            link_xpath = f"//*[@id='commonLayoutContents']/article/div[{parent_index}]/div[{child_index}]/div[@class='sc-1m4cyao-1 dYjLwF']/a"
            link_element = WebDriverWait(driver, 0.1).until(
                EC.presence_of_element_located((By.XPATH, link_xpath))
            )
            link = link_element.get_attribute("href")

            # 이미지 및 이름 XPath
            image_xpath = f"{link_xpath}/div/img"

            # 이미지 로드 확인 및 스크롤 시도
            for attempt in range(3):  # 3번까지 재시도
                try:
                    image_element = driver.find_element(By.XPATH, image_xpath)
                    name = image_element.get_attribute("alt")
                    image_src = image_element.get_attribute("src")

                    # 이미지가 None일 경우 예외 처리
                    if image_src is None:
                        raise ValueError("Image not loaded")

                    # 결과 저장
                    results.append({
                        "name": name,
                        "link": link,
                        "image": image_src
                    })
                    break  # 성공하면 루프 탈출
                except Exception:
                    print(f"Attempt {attempt + 1}: Scrolling to load image...")
                    driver.execute_script("window.scrollBy(0, 1000);")  # 스크롤 다운
                    time.sleep(0.01)  # 잠시 대기
            else:
                print(f"Image not loaded for parent {parent_index}, child {child_index}")

        except Exception as e:
            print(f"Error at parent {parent_index}, child {child_index}: {e}")
            continue

# WebDriver 종료
driver.quit()

# 실행 시간 측정을 위한 종료 시간 기록
end_time = time.time()

# 결과 출력
print("Extracted Data:")
for result in results:
    print(f"Name: {result['name']}")
    print(f"Link: {result['link']}")
    print(f"Image: {result['image']}\n")

# 총 개수 출력
print(f"Total items extracted: {len(results)}")

# 실행 시간 출력
elapsed_time = end_time - start_time
print(f"Time taken: {elapsed_time:.2f} seconds")