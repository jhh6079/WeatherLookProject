# app/__init__.py
from flask import Flask

def create_app():
    # 명시적으로 template_folder 설정
    app = Flask(__name__, template_folder='../templates',static_folder='../static')

    # API 키 및 설정 값 추가
    from key import KAKAO_API_KEY, OPENAI_API_KEY, WEATHER_API_KEY
    app.config['KAKAO_API_KEY'] = KAKAO_API_KEY
    app.config['OPENAI_API_KEY'] = OPENAI_API_KEY
    app.config['WEATHER_API_KEY'] = WEATHER_API_KEY

    # Blueprint 등록
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    return app