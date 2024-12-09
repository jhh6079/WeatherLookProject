import os
import json
import time
from threading import local, Event, Thread
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 스레드별 WebDriver를 유지하기 위한 thread-local 객체
thread_local = local()

def get_webdriver():
    """
    스레드별 WebDriver 인스턴스를 생성 또는 가져오기
    """
    if not hasattr(thread_local, "driver"):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        thread_local.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return thread_local.driver

def extract_main_data(driver, url, start_div, end_div, shared_data, data_ready_event):
    """
    메인 데이터 (이름, 링크, 이미지) 추출
    """
    driver.get(url)
    time.sleep(0.1)  # 페이지 로드 대기

    for parent_index in range(start_div, end_div + 1):
        for child_index in range(1, 4):
            try:
                link_xpath = f"//*[@id='commonLayoutContents']/article/div[{parent_index}]/div[{child_index}]/div[@class='sc-1m4cyao-1 dYjLwF']/a"
                link_element = WebDriverWait(driver, 0.1).until(
                    EC.presence_of_element_located((By.XPATH, link_xpath))
                )
                link = link_element.get_attribute("href")
                image_xpath = f"{link_xpath}/div/img"

                # 이미지 로드 확인 및 스크롤 시도
                for attempt in range(3):
                    try:
                        image_element = driver.find_element(By.XPATH, image_xpath)
                        name = image_element.get_attribute("alt")
                        image_src = image_element.get_attribute("src")

                        if image_src is None:
                            raise ValueError("Image not loaded")

                        shared_data.append({
                            "name": name,
                            "link": link,
                            "image": image_src,
                            "category": None  # 카테고리 정보를 나중에 추가
                        })
                        break
                    except Exception:
                        driver.execute_script("window.scrollBy(0, 1000);")
                        time.sleep(0.01)
                else:
                    print(f"Image not loaded for parent {parent_index}, child {child_index}")

            except Exception as e:
                print(f"Error in main data extraction (parent: {parent_index}, child: {child_index}): {e}")
                continue

    print("Main data extraction complete. Notifying second thread.")
    data_ready_event.set()

def fetch_category(item, css_selector, alternative_css_selector):
    """
    단일 링크에서 카테고리 데이터를 추출
    """
    driver = get_webdriver()
    try:
        driver.get(item['link'])

        # 첫 번째 CSS Selector 시도
        try:
            element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
            )
            category_name = element.get_attribute("data-category-name")
            if category_name:
                return category_name
        except Exception:
            print(f"First CSS Selector failed for {item['name']}.")

        # 대체 CSS Selector 사용
        try:
            element = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, alternative_css_selector))
            )
            category_name = element.get_attribute("data-category-name")
            if category_name:
                return category_name
        except Exception as e:
            print(f"Alternative CSS Selector also failed for {item['name']}: {e}")

        return None
    except Exception as e:
        print(f"Error fetching category for {item['name']}: {e}")
        return None

def parallel_category_extraction(shared_data, css_selector, alternative_css_selector, data_ready_event):
    """
    병렬로 카테고리 데이터를 추출
    """
    print("Waiting for main data to be ready...")
    data_ready_event.wait()
    print("Main data is ready. Starting parallel category extraction.")

    with ThreadPoolExecutor(max_workers=5) as executor:  # 병렬 작업 개수 제한
        futures = [
            executor.submit(fetch_category, item, css_selector, alternative_css_selector)
            for item in shared_data
        ]

        for future, item in zip(as_completed(futures), shared_data):
            try:
                category_name = future.result()
                item['category'] = category_name
                if category_name:
                    print(f"Extracted category: {category_name} for {item['name']}")
                else:
                    print(f"Failed to extract category for {item['name']}")
            except Exception as e:
                print(f"Error during parallel category extraction for {item['name']}: {e}")

def cleanup_webdrivers():
    """
    모든 스레드의 WebDriver를 종료
    """
    if hasattr(thread_local, "driver"):
        thread_local.driver.quit()
        del thread_local.driver

def create_folder(folder_name):
    """
    폴더가 없으면 생성
    """
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

def save_to_file(folder_name, file_name, data):
    """
    데이터를 JSON 파일로 저장
    """
    create_folder(folder_name)
    file_path = os.path.join(folder_name, file_name)
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

def main():
    base_url = "https://www.musinsa.com/main/musinsa/ranking?skip_bf=Y&storeCode=musinsa"

    styles = {
        "all": "199",
        "str": "203",
        "ca": "202"
    }

    genders = {
        "a": "A",
        "m": "M",
        "f": "F"
    }

    folder_name = "musinsa_data"
    all_extracted_data = {}

    for style_name, section_id in styles.items():
        for category_name in ["top", "bot"]:
            for gender_name, gender_code in genders.items():
                category_code = "001000" if style_name == "all" and category_name == "top" else "003000" if style_name == "all" and category_name == "bot" else "001" if category_name == "top" else "003"
                url = f"{base_url}&sectionId={section_id}&categoryCode={category_code}&gf={gender_code}"
                print(f"Processing URL: {url}")

                try:
                    options = webdriver.ChromeOptions()
                    options.add_argument("--headless")
                    options.add_argument("--no-sandbox")
                    options.add_argument("--disable-dev-shm-usage")

                    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

                    shared_data = []
                    data_ready_event = Event()

                    thread1 = Thread(target=extract_main_data, args=(driver, url, 2, 30, shared_data, data_ready_event))

                    start_time = time.time()
                    thread1.start()

                    parallel_category_extraction(shared_data, "#root > div.sc-1f8zq2z-0.SRIds > div.sc-ysl0re-0.UluGl > div:nth-child(3) > div > span:nth-child(2) > a.sc-147svlx-2.hTQFMT.gtm-click-button", "#root > div.sc-1f8zq2z-0.SRIds > div.sc-ysl0re-0.UluGl > div:nth-child(4) > div > span:nth-child(2) > a.sc-147svlx-2.hTQFMT.gtm-click-button", data_ready_event)

                    thread1.join()
                    driver.quit()

                    file_name = f"{style_name}_{category_name}_{gender_name}.json"
                    save_to_file(folder_name, file_name, shared_data)

                    all_extracted_data[file_name] = shared_data

                    end_time = time.time()
                    print(f"Processed {file_name} in {end_time - start_time:.2f} seconds")
                except Exception as e:
                    print(f"Error processing {style_name} {category_name} {gender_name}: {e}")

    # save_to_file(folder_name, "all_data.json", all_extracted_data)

if __name__ == "__main__":
    main()