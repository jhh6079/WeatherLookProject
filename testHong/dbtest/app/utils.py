# app/utils.py
import pandas as pd
import math
import openai


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


# 의류 추천 함수
def get_clothing_recommendation(temp, wind_speed, sky_status, precipitation_probability, openai_api_key, perceived_temp):
    prompt = (
        f"현재 온도는 {temp}도이고, 풍속은 {wind_speed} m/s, 날씨는 {sky_status}, 강수확률은 {precipitation_probability}%, 체감온도는 {perceived_temp} 입니다. , "
        "설명 없이 체감 온도만 보여주고 체감온도에 맞는 적절한 의류를 추천해줘"
    )
    openai.api_key = openai_api_key
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "당신은 날씨 전문가입니다. 날씨에 따른 적절한 의류를 추천합니다."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message['content']


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
