'''Moi sklad proxy to control the permissions'''
import requests
from base64 import b64encode
from flask import Flask, request, Response
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
PROXIED_API = 'https://online.moysklad.ru/'
MOYSKLAD_USER = 'admin@fdas'
MOYSKLAD_PASSWORD = '3f5123262483'
app.config ['SQLALCHEMY_DATABASE_URI'] = 'postgresql://peter:peter@localhost:5432/moisklad_proxy'
db = SQLAlchemy(app)

class UserAuth(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String(100)) #  this names uses only for reference
    password_hash = db.Column(db.String(265))

# class ProxyRequests(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     user = db.Column(db.Integer, db.ForeignKey('userauth.id'), nullable=False)

# class UserPermissions(db.Model):
#     pass

def encode_auth(user, password):
    return b64encode(bytes("{}:{}".format(user, password), 'ascii')).decode('ascii')

@app.route('/')
def index():
    '''Index url credentials information'''
    return 'MoySklad API proxy by Petr Kuryshev'


@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy(path):
    '''Main proxying method'''
    response = None
    excluded_req_headers = ['host', 'authorization']
    headers_dict = {name: value for (name,value) in request.headers.items()}
    if 'Authorization' in headers_dict:
        auth_type, auth_str = headers_dict['Authorization'].split(" ")
        user = UserAuth.query.filter_by(password_hash=auth_str).first()
        if user is None:
            error_resp = '{"errors":[{"error":"Ошибка аутентификации: Неправильный пароль или имя пользователя или ключ авторизации","code":1056,"moreInfo":"https://dev.moysklad.ru/doc/api/remap/1.2/#mojsklad-json-api-oshibki"}]}'
            return Response(error_resp, 401)
    else:
        # TODO: encode to JSON from dict
        error_resp = '{"errors":[{"error":"Ошибка аутентификации: Неправильный пароль или имя пользователя или ключ авторизации","code":1056,"moreInfo":"https://dev.moysklad.ru/doc/api/remap/1.2/#mojsklad-json-api-oshibki"}]}'
        return Response(error_resp, 401)
    req_headers = {name: value for (name, value) in request.headers if
                   name.lower() not in excluded_req_headers}

    req_headers['Authorization'] = 'Basic ' + \
    b64encode(bytes("{}:{}".format(MOYSKLAD_USER, MOYSKLAD_PASSWORD),
                    'ascii')).decode('ascii')
    print(request)
    if request.method == 'GET':
        resp = requests.get(f'{PROXIED_API}{path}', headers=req_headers)
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        print(resp.raw.headers.items())
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)

    elif request.method == 'POST':
        resp = requests.post(f'{PROXIED_API}{path}', json=request.get_json(),
                             headers=req_headers)
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)

    # elif request.method == 'DELETE':
    #     resp = requests.delete(f'{PROXIED_API}{path}').content
    #     response = Response(resp.content, resp.status_code, headers)

    return response


if __name__ == '__main__':
    app.run(debug=False, port=8883)
