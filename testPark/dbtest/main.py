# main.py
from app import create_app

# create_app 함수를 통해 Flask 앱 초기화
app = create_app()

if __name__ == '__main__':
    # Flask 서버 실행
    app.run(debug=True)