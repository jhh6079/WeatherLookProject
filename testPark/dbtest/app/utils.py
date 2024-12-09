# app/utils.py
import pandas as pd
import requests
import math
import openai
import re
from bs4 import BeautifulSoup

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


# 좌표 변환 함수
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



def get_clothing_recommendation(temp, wind_speed, final_status, precipitation_probability, openai_api_key, perceived_temp):
    prompt = (
        f"현재 온도는 {temp}도이고, 풍속은 {wind_speed} m/s, 날씨는 {final_status}, 강수확률은 {precipitation_probability}%, 체감온도는 {perceived_temp} 입니다."
        "체감온도와 날씨 상태에 따라 아래 형식으로 간결하게 추천해주세요. 무조건 한국말로 말해주고 그리고 형용사는 제외해주세요.:\n"
        f"체감온도는 {perceived_temp}°C,\n"
        f"날씨: {final_status}\n"
        "상의: \n하의: \n신발: \n기타:"
    )
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 날씨 전문가입니다. 날씨에 따른 적절한 의류를 상의, 하의, 신발, 기타로 간결하게 추천합니다."},
            {"role": "user", "content": prompt}
        ]
    )
    recommendation = response.choices[0]['message']['content'].strip()


    return recommendation



def crawl_fashion_data(keyword):

    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    import time

    options = webdriver.ChromeOptions()
    options.add_experimental_option("detach", True)
    # options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    url = f"https://www.musinsa.com/search/goods?keyword={keyword}"
    driver.get(url)

    results = []
    for i in range(1, 4):  # Sample range for demonstration
        try:
            link_xpath = f"//*[@id='searchList']/li[{i}]/div/a"
            image_xpath = f"{link_xpath}/img"

            link_element = WebDriverWait(driver, 1).until(EC.presence_of_element_located((By.XPATH, link_xpath)))
            image_element = driver.find_element(By.XPATH, image_xpath)

            results.append({
                "name": image_element.get_attribute("alt"),
                "link": link_element.get_attribute("href"),
                "image": image_element.get_attribute("src")
            })
        except Exception as e:
            print(f"Error: {e}")
            continue

    return results



def perceived_temperature(temp, wind_speed, sky_status, precipitation_probability, openai_api_key):
    prompt = (
        f"""
        현재 온도는 {temp}도이고, 풍속은 {wind_speed} m/s, 날씨는 {sky_status}, 강수확률은 {precipitation_probability}%입니다.
        다른 설명 없이 체감 온도를 **숫자만** 알려줘.

        예시 질문: 현재 온도는 15도이고, 풍속은 3.5 m/s, 날씨는 맑음, 강수확률은 10%입니다.
        예시 답안: 13
        
        답변은 반드시 숫자만 포함해야 합니다.
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


def get_weather_icon(sky_status):
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



import random
import re

# 불필요한 형용사 리스트
ADJECTIVES = ["따뜻한", "얇은", "두꺼운", "편안한", "멋진", "기모", "보온성 있는"]

def remove_adjectives(text):
    """
    텍스트에서 형용사를 제거하는 함수
    """
    for adj in ADJECTIVES:
        text = text.replace(adj, "").strip()  # 형용사를 제거
    return text

def extract_keywords(recommendation, category):
    """
    추천 의류 텍스트에서 지정된 카테고리(상의, 하의, 신발, 기타) 항목을 추출.
    형용사를 제거하고, '또는'이 포함된 경우 앞이나 뒤 값을 랜덤하게 반환.
    """
    pattern = rf"{category}: ([^\n]+)"  # 예: "상의: "로 시작하는 텍스트 패턴
    match = re.search(pattern, recommendation)  # 카테고리 텍스트 추출
    if match:
        raw_text = match.group(1)  # 해당 카테고리의 전체 텍스트
        cleaned_text = remove_adjectives(raw_text)  # 형용사 제거
        options = cleaned_text.split("또는")  # "또는" 기준으로 분리
        if len(options) > 1:
            # 앞 또는 뒤 값을 랜덤으로 선택하여 반환
            return random.choice(options).strip()
        return cleaned_text.split(",")[0].strip()  # 콤마로 구분된 첫 번째 값 반환
    return category  # 기본값으로 카테고리 이름 반환 (예: "상의")
