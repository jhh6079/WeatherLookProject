# app/routes.py
from typing import final

import openai
from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, session, Flask
import requests
from .utils import load_address_data, convert_to_grid, get_clothing_recommendation, get_weather_icon, \
    perceived_temperature
import pymysql

# db = pymysql.connect(host="127.0.0.1",user="root",password="8176",database="weatherlookdb")
# cursor = db.cursor()

# Blueprint 생성
bp = Blueprint('main', __name__)
weather_info = {}

@bp.route('/')  # 루트 경로
def index():
    return redirect(url_for('main.main'))  # '/main'으로 리디렉션


# 메인 페이지 라우트
@bp.route('/main', methods=['GET'])
def main():
    address_data = load_address_data()
    return render_template('index.html', address_data=address_data)


# 랭킹 페이지 라우트
@bp.route('/rank', methods=['GET'])
def rank():
    # address_data 로드
    address_data = load_address_data()
    return render_template('rank.html', address_data=address_data)


@bp.route('/summarize', methods=['POST'])
def summarize():
    try:
        json_data = request.json.get('jsonData', [])
        # 데이터를 텍스트로 변환 (LLM에 전달하기 위한 포맷)
        text_data = "\n".join([str(item) for item in json_data])

        # LLM 요약 요청
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

        summary = response.choices[0].message['content'].strip()
        return jsonify(summary)
    except Exception as e:
        print(f"요약 오류: {e}")
        return jsonify({"error": "요약 중 오류가 발생했습니다."}), 500

@bp.route('/signup', methods=['GET'])
def signup():
    # address_data 로드
    address_data = load_address_data()
    # rank.html 렌더링과 함께 address_data 전달
    return render_template('signup.html', address_data=address_data)



@bp.route('/result', methods=['POST'])
def result():
    try:
        # 입력된 데이터 가져오기
        city = request.form.get('city')
        gu = request.form.get('gu')
        dong = request.form.get('dong')

        if not city or not gu or not dong:
            return render_template('error.html', message="모든 주소를 입력하세요."), 400

        # 주소를 기반으로 좌표 변환
        address = f"{city} {gu} {dong}"
        url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
        headers = {"Authorization": f"KakaoAK {current_app.config['KAKAO_API_KEY']}"}
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            return render_template('error.html', message="주소 데이터를 가져오는 데 실패했습니다."), 500

        documents = response.json().get('documents', [])
        if not documents:
            return render_template('error.html', message=f"주소를 찾을 수 없습니다: {address}"), 404

        coords = documents[0]
        lat, lon = float(coords['y']), float(coords['x'])

        # 좌표를 기상청 격자로 변환
        nx, ny = convert_to_grid(lat, lon)

        # 문제였던 부분 욕나오는 nodata
        # 현재 시간 계산
        from datetime import datetime, timedelta

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

#여기까지


    # 기상청 API 호출
        weather_url = f"http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
        params = {
            "serviceKey": current_app.config['WEATHER_API_KEY'],
            "numOfRows": 300,  # 충분한 데이터 확보를 위해 큰 값 설정
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

        # 날씨 데이터 처리
        weather_data = weather_response.json()
        items = weather_data['response']['body']['items']['item']

        temp = next(item['fcstValue'] for item in items if item['category'] == 'TMP')
        wind_speed = next(item['fcstValue'] for item in items if item['category'] == 'WSD')
        sky_status = next(item['fcstValue'] for item in items if item['category'] == 'SKY')
        precipitation_type = next(item['fcstValue'] for item in items if item['category'] == 'PTY')
        precipitation_probability = next(item['fcstValue'] for item in items if item['category'] == 'POP')
        humidity = next(item['fcstValue'] for item in items if item['category'] == 'REH')

        # 데이터 매핑
        sky_status_map = {'1': "맑음", '3': "구름 많음", '4': "흐림"}
        precipitation_type_map = {'0': "없음", '1': "비", '2': "비/눈", '3': "눈", '4': "소나기"}

        sky_status_str = sky_status_map.get(sky_status, "알 수 없음")
        precipitation_type_str = precipitation_type_map.get(precipitation_type, "알 수 없음")

        # 최종 날씨 상태 및 아이콘 결정
        if precipitation_type in ['1', '2', '3', '4']:
            final_status = precipitation_type_str
        else:
            final_status = sky_status_str

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

        perceived_temp = perceived_temperature(
            temp, wind_speed, sky_status_str, precipitation_probability,
            current_app.config['OPENAI_API_KEY']
        )

        recommendation = get_clothing_recommendation(
            temp, wind_speed, sky_status_str, precipitation_probability,
            current_app.config['OPENAI_API_KEY'], perceived_temp
        )
        global weather_info  # 전역 변수 접근

        # 데이터를 전역 변수에 저장
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
            weather_icon_url=weather_icon_url,
            perceived_temp=perceived_temp
        )

    except Exception as e:
        print(f"오류 발생: {e}")
        return render_template('error.html', message="서버 오류가 발생했습니다."), 500


@bp.route('/login', methods=['GET', 'POST'])
def get_login():
    if request.method == 'GET':
        address_data = load_address_data()
        return render_template('login.html', address_data=address_data)

    if request.method == 'POST':
        data = request.get_json()
        login_id = data.get('login_id')
        login_ps = data.get('login_ps')

        if not login_id or not login_ps:
            return jsonify({"message":"ID 또는 비밀번호가 입력되지 않음"}), 400

        try:  # 데이터베이스 연결합니다
            conn = pymysql.connect(host="db-weatherlook-builder.ctwe8sgos8o8.us-east-2.rds.amazonaws.com", user="root",
                                   password="20020414", database="weatherlookdb")
            cursor = conn.cursor()

            cursor.execute("select username, password, nickname from weatherlookdb_user where username = %s AND password = %s", (login_id, login_ps))
            user = cursor.fetchone()

            if user:
                username, password, nickname = user
                #세션에 사용자 정보 저장
                session['username'] = username
                session['password'] = password
                session['nickname'] = nickname
                return jsonify({"message" : f"로그인 성공, 축하드립니다 {nickname} 님."}), 200
            else:
                return jsonify({"message" : "ID와 비밀번호를 확인바랍니다"}), 401

        except pymysql.MySQLError as err:
            print(f"DB 에러: {err}")
            return jsonify({"message": "데이터베이스 오류 발생"}), 500

#사용자 확인 특정 라우트에서 사용자가 로그인했는지 확인하려면 session 데이터를 참조
@bp.route('/dashboard')
def dashboard():
    if 'username' in session:
        return f"안녕하세요, {session['nickname']} 님! 대시보드에 오신 것을 환영합니다."
    else:
        return "로그인이 필요합니다.", 401

# 로그아웃 처리 사용자가 로그아웃할 때 session 데이터를 삭제
@bp.route('/logout')
def logout():
    session.clear()  # 모든 세션 데이터 삭제
    return jsonify({"message": "로그아웃 성공!"}), 200

@bp.route('/register', methods=['GET', 'POST'])
def get_register():
    if request.method == 'GET':
        # GET 요청 시 회원가입 양식 페이지 렌더링
        address_data = load_address_data()
        return render_template('signup.html', address_data=address_data)

    if request.method == 'POST':
        # POST 요청 시 데이터 처리
        data = request.get_json()
        signup_id = data.get('signup_id')
        signup_ps = data.get('signup_ps')
        signup_name = data.get('signup_name')

        if not signup_id or not signup_ps or not signup_name:
            return jsonify({"message": "ID, PS, 이름 전부 입력바람"}), 400

        try:  # 데이터베이스 연결합니다
            conn = pymysql.connect(host="db-weatherlook-builder.ctwe8sgos8o8.us-east-2.rds.amazonaws.com", user="root",
                                   password="20020414", database="weatherlookdb")
            cursor = conn.cursor()

            # 중복체크
            cursor.execute("select username from weatherlookdb_user where username = %s", (signup_id,))
            if cursor.fetchone():
                return jsonify({'message': '아이디가 이미 존재...'}), 409

            # 회원가입 데이터 삽입부분
            cursor.execute("INSERT INTO weatherlookdb_user (username, password, nickname) VALUES (%s, %s, %s)",
                           (signup_id, signup_ps, signup_name))
            conn.commit()

            return jsonify({'message': '회원가입 성공! 축하'}), 201

        except pymysql.connect.Error as err:
            print(f'아이 X발 에러났어: {err}')
            return jsonify({'message': 'db 오류났다능... 킹받는당'}), 500


@bp.route('/get_coords', methods=['POST'])
def get_coords():
    try:
        data = request.json
        address = f"{data['city']} {data['gu']} {data['dong']}"
        url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
        headers = {"Authorization": f"KakaoAK {current_app.config['KAKAO_API_KEY']}"}
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            documents = response.json().get('documents', [])
            if documents:
                coords = documents[0]
                return jsonify({'lat': coords['y'], 'lon': coords['x']})
            else:
                return jsonify({'error': f'주소를 찾을 수 없습니다: {address}'}), 404
        else:
            return jsonify({'error': f'Kakao API 오류: {response.status_code}'}), 500
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({'error': '서버 오류가 발생했습니다.'}), 500

@bp.route('/ask_question', methods=['POST'])
def ask_question():
    global weather_info
    try:
        data = request.json
        question = data['question']

        additional_info = ""
        hourly_data = weather_info.get("hourly_data", [])

        if hourly_data:
            hourly_summaries = [
                f"{hour['time'][:2]}:{hour['time'][2:]}: {hour['temperature']}°C, {hour['sky']}"
                for hour in hourly_data[:5]
            ]
            hourly_summary_text = "<br>".join(hourly_summaries)  # HTML 줄바꿈
            additional_info += f"시간별 요약:<br>{hourly_summary_text}.<br>"

        if weather_info:
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

        answer = response.choices[0].message['content'].strip()
        return jsonify({"answer": answer})

    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"error": "서버 오류가 발생했습니다."}), 500


@bp.route('/save_clothing', methods=['POST'])
def save_clothing():
    try:
        data = request.json
        clothing = data.get('clothing', '')
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": (
                    "다음과 같은 지문에서 의류 부분만 골라서 저장해줘.\n\n"
                    "예시 입력:\n"
                    "\"체감 온도가 약 7도 정도로 예상되므로, 더 따뜻하게 입고 싶으시다면 다음과 같은 추가 의류를 고려해보세요:\n"
                    "- 두꺼운 스웨터나 후드티\n"
                    "- 보온성이 높은 패딩 조끼 추가\n"
                    "- 기모가 있는 바지 또는 두꺼운 층의 바지\n"
                    "- 두꺼운 장갑이나 털 장갑으로 손 보호\n"
                    "- 목도리나 머플러를 추가하여 목 부위 보온\"\n\n"

                    "예시 출력:\n"
                    "상의 : 두꺼운 스웨터, 후드티, 패딩 조끼\n"
                    "하의 : 기모 바지, 두꺼운 바지\n"
                    "기타 : 장갑, 목도리, 머플러\n\n"
                    "추가 조건: \"기모가 있는 긴 바지\"라는 항목이 있다면,  '기모 바지' 만 남겨줘.\n"
                    ". '두꺼운 외투'처럼 너무 넓은 범위의 의류 항목은 제외해줘.\n"
                    "\"따뜻한 머플러\"라면 '따뜻한' 같은 형용사도 제외하고 '머플러'만 남겨줘.\n\n"
                    "위와 같은 형식으로 의류 부분만 추출해서 출력해줘    ."

                )},
                {"role": "user", "content": f"{clothing}"},
            ]
        )

        answer = response.choices[0].message['content'].strip()

        if answer:
            # 의류 추천을 저장하지 않고 출력만 하는 부분
            print(f"저장된 의류 추천: \n{answer}")
            return jsonify({"message": "의류 추천이 출력되었습니다."})
        else:
            return jsonify({"message": "출력할 의류 추천이 없습니다."}), 400
    except Exception as e:
        print(f"오류 발생: {e}")
        return jsonify({"error": "출력 중 오류가 발생했습니다."}), 500