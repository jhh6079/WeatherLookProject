# app/routes.py
from typing import final

import openai
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, session, Flask
import requests

from .utils import load_address_data, convert_to_grid, get_clothing_recommendation, get_weather_icon, perceived_temperature
from .utils import crawl_fashion_data
from .utils import extract_keywords
import pymysql

bp = Blueprint('main', __name__)  # Flask Blueprint 생성
weather_info = {}  # 전역 변수로 날씨 정보를 저장

# 홈 경로: main으로 다시 보냄.
@bp.route('/')
def index():
    return redirect(url_for('main.main'))

# 메인 페이지 렌더링
@bp.route('/main', methods=['GET'])
def main():
    address_data = load_address_data()  # 주소 데이터 로드
    return render_template('index.html', address_data=address_data)

# 랭킹 페이지 렌더링
@bp.route('/rank', methods=['GET'])
def rank():
    address_data = load_address_data()  # 주소 데이터 로드
    return render_template('rank.html', address_data=address_data)

# LLM 기반 요약 API
@bp.route('/summarize', methods=['POST'])
def summarize():
    try:
        # 클라이언트에서 받은 JSON 데이터를 텍스트로 변환
        json_data = request.json.get('jsonData', [])
        text_data = "\n".join([str(item) for item in json_data])

        # OpenAI API를 통해 요약 처리
        openai.api_key = current_app.config['OPENAI_API_KEY']
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "요약은 아래의 기준에 따라 작성해줘:\n\n"
                        " 전체적인 결론:\n"
                        " 데이터를 분석한 결과를 간략히 정리해 줘.\n\n"
                        "JSON 데이터는 다음과 같은 형식입니다:\n"
                        "{\n"
                        "  \"categories\": [\n"
                        "    {\"category\": \"상의\", \"items\": [\"티셔츠\", \"셔츠\"]},\n"
                        "    {\"category\": \"바지\", \"items\": [\"청바지\", \"슬랙스\"]}\n"
                        "  ]\n"
                        "}\n\n"
                        "결론은 2줄로 해줘"
                        "문자 같은건 쓰지마 예시로 * # "
                        "위 기준에 따라 요약을 작성해 주세요."
                    )
                },
                {
                    "role": "user",
                    "content": text_data
                }
            ]
        )
        summary = response.choices[0].message['content'].strip()  # 요약 결과 가져오기
        return jsonify(summary)  # JSON 형태로 반환
    except Exception as e:
        print(f"요약 오류: {e}")
        return jsonify({"error": "요약 중 오류가 발생했습니다."}), 500

# 회원가입 페이지 렌더링
@bp.route('/signup', methods=['GET'])
def signup():
    address_data = load_address_data()  # 주소 데이터 로드
    return render_template('signup.html', address_data=address_data)

@bp.route('/get_coords', methods=['POST'])
def get_coords():
    try:
        # 카카오 API를 사용해 주소를 위도/경도로 변환
        data = request.json
        address = f"{data['city']} {data['gu']} {data['dong']}"
        url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
        headers = {"Authorization": f"KakaoAK {current_app.config['KAKAO_API_KEY']}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            # API 응답 처리
            documents = response.json().get('documents', [])
            if documents:
                coords = documents[0]
                return jsonify({'lat': coords['y'], 'lon': coords['x']})
            else:
                return jsonify({'error': f'주소를 찾을 수 없습니다: {address}'}), 404
        else:
            # API 오류 처리
            return jsonify({'error': f'Kakao API 오류: {response.status_code}'}), 500
    except Exception as e:
        # 서버 오류 처리
        print(f"오류 발생: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

# 날씨 정보 처리 및 결과 페이지 렌더링
@bp.route('/result', methods=['POST'])
def result():
    try:
        # 클라이언트에서 위도와 경도 수신
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        if latitude and longitude:
            # Kakao API를 이용해 위도/경도를 주소로 변환
            url = f"https://dapi.kakao.com/v2/local/geo/coord2address.json?x={longitude}&y={latitude}"
            headers = {"Authorization": f"KakaoAK {current_app.config['KAKAO_API_KEY']}"}
            response = requests.get(url, headers=headers)

            if response.status_code != 200:  # API 응답 실패 시 처리
                return render_template('error.html', message="위치 데이터를 가져오는 데 실패했습니다."), 500

            documents = response.json().get('documents', [])
            if not documents:
                return render_template('error.html', message="현재 위치의 주소를 찾을 수 없습니다."), 404

            address = documents[0].get('address', {})
            city = address.get('region_1depth_name')  # 시/도 이름
            gu = address.get('region_2depth_name')    # 구 이름
            dong = address.get('region_3depth_name')  # 동 이름

        else:
            # 입력된 주소 데이터 확인
            city = request.form.get('city')
            gu = request.form.get('gu')
            dong = request.form.get('dong')

            if not city or not gu or not dong:
                return render_template('error.html', message="모든 주소를 입력하세요."), 400

        # 주소로 좌표 검색
        address = f"{city} {gu} {dong}"
        url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
        headers = {"Authorization": f"KakaoAK {current_app.config['KAKAO_API_KEY']}"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:  # API 응답 실패 시 처리
            return render_template('error.html', message="주소 데이터를 가져오는 데 실패했습니다."), 500

        documents = response.json().get('documents', [])
        if not documents:  # 주소를 찾을 수 없는 경우
            return render_template('error.html', message=f"주소를 찾을 수 없습니다: {address}"), 404

        coords = documents[0]
        lat, lon = float(coords['y']), float(coords['x'])  # 좌표 변환

        # 위,경도를 기상청 격자로 변환
        nx, ny = convert_to_grid(lat, lon)

        from datetime import datetime, timedelta

        # 현재 시간 기준으로 기상청 API 요청 시간 계산
        now = datetime.now()
        base_date = now.strftime("%Y%m%d")

        # 기상청 API 제공 시간 기준으로 base_time 계산
        if now.hour < 2 or (now.hour == 2 and now.minute < 10):
            base_time = "2300"
            base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
        elif now.hour < 5 or (now.hour == 5 and now.minute < 10):
            base_time = "0200"
        elif now.hour < 8 or (now.hour == 8 and now.minute < 10):
            base_time = "0500"
        elif now.hour < 11 or (now.hour == 11 and now.minute < 10):
            base_time = "0800"
        elif now.hour < 14 or (now.hour == 14 and now.minute < 10):
            base_time = "1100"
        elif now.hour < 17 or (now.hour == 17 and now.minute < 10):
            base_time = "1400"
        elif now.hour < 20 or (now.hour == 20 and now.minute < 10):
            base_time = "1700"
        elif now.hour < 23 or (now.hour == 23 and now.minute < 10):
            base_time = "2000"
        else:
            base_time = "2300"

        # 기상청 API 호출
        weather_url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        params = {
            "serviceKey": current_app.config['WEATHER_API_KEY'],
            "numOfRows": 300,
            "pageNo": 1,
            "dataType": "JSON",
            "base_date": base_date,
            "base_time": base_time,
            "nx": nx,
            "ny": ny
        }
        weather_response = requests.get(weather_url, params=params)

        if weather_response.status_code != 200:
            return render_template('error.html', message="날씨 데이터를 가져오는 데 실패했습니다."), 500

        # 날씨 데이터 파싱
        weather_data = weather_response.json()
        items = weather_data['response']['body']['items']['item']

        temp = next(item['fcstValue'] for item in items if item['category'] == 'TMP')  # 온도
        wind_speed = next(item['fcstValue'] for item in items if item['category'] == 'WSD')  # 풍속
        sky_status = next(item['fcstValue'] for item in items if item['category'] == 'SKY')  # 하늘 상태
        precipitation_type = next(item['fcstValue'] for item in items if item['category'] == 'PTY')  # 강수 형태
        precipitation_probability = next(item['fcstValue'] for item in items if item['category'] == 'POP')  # 강수 확률
        humidity = next(item['fcstValue'] for item in items if item['category'] == 'REH')  # 습도

        # 실시간 하늘 상태와 강수 형태를 매핑
        sky_status_map = {'1': "맑음", '3': "구름 많음", '4': "흐림"}
        precipitation_type_map = {'0': "없음", '1': "비", '2': "비/눈", '3': "눈", '4': "소나기"}

        sky_status_str = sky_status_map.get(sky_status, "알 수 없음")
        precipitation_type_str = precipitation_type_map.get(precipitation_type, "알 수 없음")

        # 매핑된 날씨 상태를 최종적으로 결정
        if precipitation_type in ['1', '2', '3', '4']:
            final_status = precipitation_type_str
        else:
            final_status = sky_status_str

        # 아이콘 URL 가져오기
        weather_icon_url = get_weather_icon(final_status)

        # 현재 시간 및 24시간 이후 시간 계산
        now_date = now.strftime("%Y%m%d")
        current_time = (now + timedelta(hours=1)).replace(minute=0, second=0).strftime("%H%M")
        end_time = now + timedelta(hours=24)
        end_date = end_time.strftime("%Y%m%d")
        end_time_str = end_time.strftime("%H%M")

        # 시간별 데이터 필터링
        hourly_data = []
        for item in items:
            if item['category'] == 'TMP':
                hourly_entry = {
                    "date": item['fcstDate'],
                    "time": item['fcstTime'],
                    "temperature": item['fcstValue'],
                    "sky": None,
                    "icon": None
                }

                precipitation_type = None
                sky_status = None

                for other_item in items:
                    if other_item['fcstDate'] == item['fcstDate'] and other_item['fcstTime'] == item['fcstTime']:
                        if other_item['category'] == 'PTY':
                            precipitation_type = other_item['fcstValue']
                        elif other_item['category'] == 'SKY':
                            sky_status = other_item['fcstValue']

                sky_status_str = sky_status_map.get(sky_status, "알 수 없음")
                precipitation_type_str = precipitation_type_map.get(precipitation_type, "알 수 없음")
                if precipitation_type in ['1', '2', '3', '4']:
                    final_sky_status = precipitation_type_str
                else:
                    final_sky_status = sky_status_str

                hourly_entry["sky"] = final_sky_status
                hourly_entry["icon"] = get_weather_icon(final_sky_status)
                hourly_data.append(hourly_entry)

        filtered_data = [
            data for data in hourly_data
            if (data['date'] > now_date or (data['date'] == now_date and int(data['time']) >= int(current_time))) and
               (data['date'] < end_date or (data['date'] == end_date and int(data['time']) <= int(end_time_str)))
        ]

        filtered_data.sort(key=lambda x: (x['date'], x['time']))

        # 체감 온도 계산
        perceived_temp = perceived_temperature(
            temp, wind_speed, sky_status_str, precipitation_probability,
            current_app.config['OPENAI_API_KEY']
        )

        # 의류 추천 계산
        recommendation = get_clothing_recommendation(
            temp, wind_speed, sky_status_str, precipitation_probability,
            current_app.config['OPENAI_API_KEY'], perceived_temp
        )

        # 전역 변수에 날씨 데이터 저장
        global weather_info
        weather_info = {
            "city": city,
            "gu": gu,
            "dong": dong,
            "lat": lat,
            "lon": lon,
            "temperature": temp,
            "wind_speed": wind_speed,
            "sky_status": final_status,
            "precipitation_type": precipitation_type_str,
            "precipitation_probability": precipitation_probability,
            "humidity": humidity,
            "clothing_recommendation": recommendation,
            "hourly_data": filtered_data,
            "weather_icon_url": weather_icon_url,
            "perceived_temp": perceived_temp
        }

        # 카테고리별 패션 데이터 크롤링
        categories = ["상의", "하의", "신발"]
        fashion_data = {}

        for category in categories:
            keyword = extract_keywords(recommendation, category)
            fashion_data[category] = crawl_fashion_data(keyword)

        # 결과 페이지 렌더링
        return render_template(
            'result.html',
            city=city,
            gu=gu,
            dong=dong,
            lat=lat,
            lon=lon,
            temperature=temp,
            wind_speed=wind_speed,
            sky_status=final_status,
            precipitation_type=precipitation_type_str,
            precipitation_probability=precipitation_probability,
            humidity=humidity,
            clothing_recommendation=recommendation,
            hourly_data=filtered_data,
            fashion_data=fashion_data,
            weather_icon_url=weather_icon_url,
            perceived_temp=perceived_temp
        )
    except Exception as e:
        print(f"오류 발생: {e}")
        return render_template('error.html', message="서버 오류가 발생했습니다."), 500

# 로그인 및 회원가입 구현 코드
# @bp.route('/login', methods=['GET', 'POST'])
# def get_login():
#     # GET 요청 처리: 로그인 페이지 렌더링
#     if request.method == 'GET':
#         address_data = load_address_data()
#         return render_template('login.html', address_data=address_data)
#
#     # POST 요청 처리: 로그인 인증
#     if request.method == 'POST':
#         data = request.get_json()
#         login_id = data.get('login_id')
#         login_ps = data.get('login_ps')
#
#         # 로그인 실패 시 처리 메세지
#         if not login_id or not login_ps:
#             return jsonify({"message":"ID 또는 비밀번호가 입력되지 않음"}), 400
#
#         try:
#             # MYSQL 데이터베이스에 연결
#             conn = pymysql.connect(
#                 host="db-weatherlook-builder.ctwe8sgos8o8.us-east-2.rds.amazonaws.com",
#                 user="root",
#                 password="20020414",
#                 database="weatherlookdb"
#             )
#             cursor = conn.cursor()
#
#             # 사용자 인증
#             cursor.execute(
#                 "select username, password, nickname from weatherlookdb_user where username = %s AND password = %s",
#                 (login_id, login_ps)
#             )
#             user = cursor.fetchone()
#
#             if user:
#                 # 세션 설정
#                 username, password, nickname = user
#                 session['username'] = username
#                 session['password'] = password
#                 session['nickname'] = nickname
#                 return jsonify({"message" : f"로그인 성공, 축하드립니다 {nickname} 님."}), 200
#             else:
#
#                 return jsonify({"message" : "ID와 비밀번호를 확인바랍니다."}), 401
#
#         except pymysql.MySQLError as err:
#             # DB 에러 처리
#             print(f"DB 에러: {err}")
#             return jsonify({"message": "데이터베이스 오류 발생"}), 500
#
# @bp.route('/dashboard')
# def dashboard():
#     # 세션 체크 후 Dashboard에 접근
#     if 'username' in session:
#         return f"안녕하세요, {session['nickname']} 님! 대시보드에 오신 것을 환영합니다."
#     else:
#         return "로그인이 필요합니다.", 401
#
# @bp.route('/logout')
# def logout():
#     # 세션 초기화 및 로그아웃 처리
#     session.clear()
#     return jsonify({"message": "로그아웃 성공!"}), 200
#
# @bp.route('/register', methods=['GET', 'POST'])
# def get_register():
#     # GET 요청 처리: 회원가입 페이지 렌더링
#     if request.method == 'GET':
#         address_data = load_address_data()
#         return render_template('signup.html', address_data=address_data)
#
#     # POST 요청 처리: 회원가입 처리
#     if request.method == 'POST':
#         data = request.get_json()
#         signup_id = data.get('signup_id')
#         signup_ps = data.get('signup_ps')
#         signup_name = data.get('signup_name')
#
#
#         if not signup_id or not signup_ps or not signup_name:
#             return jsonify({"message": "ID, PS, 이름 전부 입력바람"}), 400
#
#         try:
#             # MYSQL 데이터베이스에 연결
#             conn = pymysql.connect(
#                 host="db-weatherlook-builder.ctwe8sgos8o8.us-east-2.rds.amazonaws.com",
#                 user="root",
#                 password="20020414",
#                 database="weatherlookdb"
#             )
#             cursor = conn.cursor()
#
#             # 중복 확인
#             cursor.execute("select username from weatherlookdb_user where username = %s", (signup_id,))
#             if cursor.fetchone():
#                 return jsonify({'message': '아이디가 이미 존재합니다.'}), 409
#
#             # 회원가입에 저장된 사용자 등록
#             cursor.execute(
#                 "INSERT INTO weatherlookdb_user (username, password, nickname) VALUES (%s, %s, %s)",
#                 (signup_id, signup_ps, signup_name)
#             )
#             conn.commit()
#
#             return jsonify({'message': '회원가입 성공하였습니다! 축하합니다.!'}), 201
#
#         except pymysql.connect.Error as err:
#
#             print(f'데이터베이스가 에러났습니다. 오류를 확인해주세요....: {err}')
#             return jsonify({'message': '데이터베이스가 에러났습니다. 오류를 확인해주세요....'}), 500


@bp.route('/ask_question', methods=['POST'])
def ask_question():
    global weather_info  # 날씨 정보 변수 사용
    try:
        # 질문 데이터 처리
        data = request.json
        question = data['question']

        # 추가 정보 생성
        additional_info = ""
        hourly_data = weather_info.get("hourly_data", [])

        if hourly_data:
            # 시간별에 따른 날씨 데이터 요약 생성
            hourly_summaries = [
                f"{hour['time'][:2]}:{hour['time'][2:]}: {hour['temperature']}°C, {hour['sky']}"
                for hour in hourly_data[:5]
            ]
            hourly_summary_text = "<br>".join(hourly_summaries)  # HTML 줄바꿈
            additional_info += f"시간별 요약:<br>{hourly_summary_text}.<br>"

        if weather_info:
            # 현재 날씨에 대한 정보 추가
            temperature = weather_info['temperature']
            description = weather_info['sky_status']
            wind_speed = weather_info['wind_speed']
            clothing_recommendation = weather_info['clothing_recommendation']

            additional_info += (
                f"현재 기온은 {temperature}°C<br>"
                f"날씨는 {description}<br>"
                f"바람 속도는 {wind_speed}m/s<br>"
                f"추천 의류: {clothing_recommendation}.<br>"
            )

        # OpenAI GPT 모델 호출 및 메세지 전달
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "당신은 날씨 및 의류 전문가입니다. "
                        f"{additional_info} 시간별 데이터와 현재 날씨를 참고하여 "
                        "질문에 정확하고 적절한 설명을 제시해주세요."
                        "\n\n"
                        "예시는 다음과 같은 형식으로 작성해주세요:"
                        "\n12시(7°C, 비)"
                        "\n상의: [추천 내용]"
                        "\n하의: [추천 내용]"
                        "\n신발: [추천 내용]"
                        "\n기타: [추천 내용]"
                        "\n"
                        "모르는 정보는 대답하지마."
                        "사용자가 더 쉽게 읽을 수 있도록 줄바꿈을 명확히 포함하여 작성해주세요."
                    ),
                },
                {"role": "user", "content": question},
            ]
        )

        # 답변 반환
        answer = response.choices[0].message['content'].strip()
        return jsonify({"answer": answer})

    except Exception as e:
        # 서버 오류 처리
        print(f"오류 발생: {e}")
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500

