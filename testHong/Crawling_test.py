from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Selenium WebDriver 설정
options = webdriver.ChromeOptions()
options.add_argument("--headless")
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
            link_element = WebDriverWait(driver, 1).until(
                EC.presence_of_element_located((By.XPATH, link_xpath))
            )
            link = link_element.get_attribute("href")

            # 이미지 및 이름 XPath
            image_xpath = f"{link_xpath}/div/img"
            image_element = driver.find_element(By.XPATH, image_xpath)
            name = image_element.get_attribute("alt")
            image_src = image_element.get_attribute("src")

            # 결과 저장
            results.append({
                "name": name,
                "link": link,
                "image": image_src
            })
        except Exception as e:
            print(f"Error at parent {parent_index}, child {child_index}: {e}")
            continue

# WebDriver 종료
driver.quit()

# 결과 출력
print("Extracted Data:")
for result in results:
    print(f"Name: {result['name']}")
    print(f"Link: {result['link']}")
    print(f"Image: {result['image']}\n")

# 총 개수 출력
print(f"Total items extracted: {len(results)}")