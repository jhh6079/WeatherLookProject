# app/utils.py
import pandas as pd
import requests
import random
import math
import openai
import re
import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor



# 주소 데이터 로드 함수
def load_address_data():
    df = pd.read_excel("전국_읍면동_주소.xlsx")
    df.columns = ["시/도", "구/군", "읍/면/동"]
    df = df.loc[:, ["시/도", "구/군", "읍/면/동"]]

    address_dict = {}
    for _, row in df.iterrows():
        city = row["시/도"]
        gu = row["구/군"]
        dong = row["읍/면/동"]

        if city not in address_dict:
            address_dict[city] = {}
        if gu not in address_dict[city]:
            address_dict[city][gu] = []
        address_dict[city][gu].append(dong)
    return address_dict


# 격좌 좌표 변환 함수 (그리드 형식)
def convert_to_grid(lat, lon):
    RE = 6371.00877
    GRID = 5.0
    SLAT1 = 30.0
    SLAT2 = 60.0
    OLON = 126.0
    OLAT = 38.0
    XO = 43.0
    YO = 136.0

    DEGRAD = math.pi / 180.0
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = int(math.floor(ra * math.sin(theta) + XO + 0.5))
    ny = int(math.floor(ro - ra * math.cos(theta) + YO + 0.5))
    return nx, ny


# 의류 추천 함수 ('의류를 추천' 하는 부분에 해당됨)
def get_clothing_recommendation(temp, wind_speed, final_status, precipitation_probability, openai_api_key, perceived_temp):
    prompt = (
        f"현재 온도는 {temp}도이고, 풍속은 {wind_speed} m/s, 날씨는 {final_status}, 강수확률은 {precipitation_probability}%, 체감온도는 {perceived_temp} 입니다."
        "체감온도와 날씨 상태에 따라 아래 형식으로 간결하게 추천해주세요. 추가로 무조건 한국말로 말해주고 형용사는 제외해주세요:\n"
        f"현재 온도는 {temp}도이고, 풍속은 {wind_speed} m/s, 날씨는 {final_status}, 강수확률은 {precipitation_probability}%, 체감온도는 {perceived_temp} 입니다."
        f"상의는 겨울에는 보통 패딩류나 울 자켓류로 추천해주지만 {final_status}에 맞게 추천해줘, 여름에는 반팔티나 나시류를 대부분 추천해주지만 {final_status}에 맞게 추천해주세요.\n"
        f"하의는 겨울에 맞는 바지를 제시해주고, 대신 겨울이어도 {final_status}에 맞게 추천해줘, 여름에도 똑같이 적용해주세요.\n"
        f"상,하의를 추천해줄 때 두 개 이상을 추천해주게 되면 '또는' 이라는 말만 사용해줘!\n"
        
        f"체감온도: {perceived_temp}°C,\n"
         "현재기온: {temp}\n"
         "상의: 하의: 신발: 기타:"
    )
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 날씨 전문가입니다. 날씨에 따른 적절한 의류를 상의, 하의, 신발, 기타로 간결하게 추천합니다."},
            {"role": "user", "content": prompt}
        ]
    )
    recommendation = response.choices[0].message['content'].replace("\n", "<br>")
    return response.choices[0].message['content']


# 불필요한 형용사 리스트
ADJECTIVES = ["따뜻한", "얇은", "두꺼운", "편안한", "멋진","보온성 있는","두툼한", "두터운"]

# 텍스트에서 형용사를 제거하는 함수
def remove_adjectives(text):
    """
    텍스트에서 형용사를 제거하는 함수
    """
    for adj in ADJECTIVES:
        text = text.replace(adj, "").strip()  # 형용사를 제거
    return text

# 추천 의류 텍스트에서 지정된 카테고리(상의, 하의, 신발, 기타) 항목을 추출하는 함수
def extract_keywords(recommendation, category):
    """
    추천 의류 텍스트에서 지정된 카테고리(상의, 하의, 신발, 기타) 항목을 추출.
    형용사를 제거하고, '또는'이 포함된 경우 앞이나 뒤 값을 랜덤하게 반환.
    """
    pattern = rf"{category}: ([^\n]+)"
    match = re.search(pattern, recommendation)  # 카테고리별 텍스트를 추출
    if match:
        raw_text = match.group(1)
        cleaned_text = remove_adjectives(raw_text)  # 형용사 제거
        options = cleaned_text.split("또는")  # "또는" 기준으로 분리
        if len(options) > 1:
            # <추천된 값> 또는 <추천된 값> 둘 중 값을 랜덤으로 선택하여 반환
            return random.choice(options).strip()
        return cleaned_text.split(",")[0].strip()  # 콤마(",")로 구분하여 분리
    return category

def crawl_fashion_data(keyword, start_div=2, end_div=3, max_attempts=3):

    # 실행 시간 측정 시작
    start_time = time.time()

    # Selenium WebDriver 설정
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # 헤드리스 모드 (브라우저를 띄우지 않고 실행)
    options.add_argument("--no-sandbox")  # 리눅스 환경에서 필요한 옵션
    options.add_argument("--disable-dev-shm-usage")  # 메모리 부족 문제 방지

    # Chrome WebDriver 초기화
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Musinsa 페이지 URL 설정 (검색어 기반)
    url = f"https://www.musinsa.com/search/goods?keyword={keyword}&gf=A"
    driver.get(url)

    # 크롤링 결과를 저장할 리스트
    results = []

    try:
        # 부모 및 자식 인덱스 조합 생성 (지정된 범위 내에서 부모-자식 관계 탐색)
        parent_child_combinations = [
            (parent_index, child_index)
            for parent_index in range(start_div, end_div + 1)
            for child_index in range(1, 5)
        ]
        random.shuffle(parent_child_combinations)  # 탐색 순서를 무작위로 섞음(항상 다른 결과를 나타내기 위함)

        # 부모-자식 인덱스 조합을 순회하며 데이터 추출
        for parent_index, child_index in parent_child_combinations:
            try:
                # 상품 링크의 XPath 지정
                link_xpath = (
                    f"//*[@id='commonLayoutContents']/div/div[contains(@class, 'sc-x7dw99-2')]/div/div/div/div[{parent_index}]/div/div[{child_index}]/div/div[contains(@class, 'sc-fLseNd')]/div/a"
                )
                # XPath를 통해 상품 링크 요소 대기
                link_element = WebDriverWait(driver, 0.5).until(
                    EC.presence_of_element_located((By.XPATH, link_xpath))
                )
                link = link_element.get_attribute("href")  # 링크 추출

                # 이미지 및 이름 XPath
                image_xpath = f"{link_xpath}/div/img"

                # 이미지 로드 확인 및 스크롤 시도
                for attempt in range(max_attempts):  # 최대 시도 횟수만큼 반복
                    try:
                        # 이미지 요소 가져오기
                        image_element = driver.find_element(By.XPATH, image_xpath)
                        name = image_element.get_attribute("alt")  # 상품명 추출
                        image_src = image_element.get_attribute("src")  # 이미지 URL 추출


                        if image_src is None:
                            raise ValueError("Image not loaded")

                        # 결과 저장
                        results.append({
                            "name": name, # 상품명
                            "link": link,  # 상품 링크
                            "image": image_src # 상품 이미지
                        })
                        break
                    except Exception:
                        # 실패 시 스크롤을 내려 이미지 로드 시도
                        print(f"Attempt {attempt + 1}: Scrolling to load image...")
                        driver.execute_script("window.scrollBy(0, 1000);")  # 스크롤 다운
                        time.sleep(0.01)  # 0.01초 동안 잠시 대기
                else:

                    print(f"Image not loaded for parent {parent_index}, child {child_index}")

            except Exception as e:

                print(f"Error at parent {parent_index}, child {child_index}: {e}")
                continue
    finally:
        # 작업 완료 후 WebDriver 종료
        driver.quit()

    # 실행 시간 측정 종료
    end_time = time.time()


    elapsed_time = end_time - start_time
    print(f"Time taken: {elapsed_time:.2f} seconds")

    return results


# LLM을 활용하여 체감온도를 알려주는 함수
def perceived_temperature(temp, wind_speed, sky_status, precipitation_probability, openai_api_key):
    prompt = (
        f"""
        현재 온도는 {temp}도이고, 풍속은 {wind_speed} m/s, 날씨는 {sky_status}, 강수확률은 {precipitation_probability}%입니다.
        다른 설명 없이 체감 온도를 **숫자만** 알려줘.

        예시 질문: 현재 온도는 15도이고, 풍속은 3.5 m/s, 날씨는 맑음, 강수확률은 10%입니다.
        예시 답안: 13
        
        답변은 반드시 숫자만 포함해야 합니다.
        모르는 정보는 대답하지마.
        """

    )
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 날씨 전문가입니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']

# 날씨 상태에 따른 아이콘 URL을 반환하는 함수
def get_weather_icon(sky_status):
    # 날씨 상태별 아이콘 URL 매핑
    icon_map = {
        "맑음": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt1.svg",
        "구름 많음": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt5.svg",
        "흐림": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt7.svg",
        "비": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt9.svg",
        "눈": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt12.svg",
        "비/눈": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt21.svg",
        "소나기": "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt15.svg",
    }
    return icon_map.get(sky_status, "https://ssl.pstatic.net/sstatic/keypage/outside/scui/weather_new_new/img/weather_svg/icon_flat_wt1.svg")
