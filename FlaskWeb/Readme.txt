git clone https://github.com/ldh901024/ldhpublic.git

[root@localhost FlaskWeb]# source venv/bin/activate

패키지 설치
(venv) [root@localhost FlaskWeb]# pip install -r requirements.txt

실행
(venv) [root@localhost FlaskWeb]# python3 app.py


접속포트 수정은 app.py 맨하단에서 진행.

if __name__ == '__main__':
    with app.app_context():
        setup_event_listeners()  # 애플리케이션 컨텍스트 내에서 이벤트 리스너 설정
    app.run(host="0.0.0.0", port=5000)         <---------------------수정

