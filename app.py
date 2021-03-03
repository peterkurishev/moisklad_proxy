"""Moi sklad proxy to control the permissions"""
import os
import json
from base64 import b64encode

import secrets
import requests
from flask import Flask, request, Response
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
PROXIED_HOST = os.environ.get("PROXIED_HOST", default="online.moysklad.ru")
PROXIED_API = 'https://{}/'.format(PROXIED_HOST)
PROXY_HOST = os.environ.get("PROXY_HOST", default="moisklad.vsdg.ru")
MOYSKLAD_USER = os.environ.get("MOYSKLAD_USER", default="user")
MOYSKLAD_PASSWORD = os.environ.get("MOYSKLAD_PASSWORD", default="password")
ONLY_FLAGGED_PRODUCTS = 'filter=https://online.moysklad.ru/api/remap/1.2/entity/product/metadata/attributes/ccade007-6f68-11eb-0a80-0771002843d1=true'
app.config[
    'SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL",
                                                default='postgresql://moisklad:moisklad@localhost:5432/moisklad_proxy')
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
app.config['SECRET_KEY'] = secrets.token_urlsafe(16)
db = SQLAlchemy(app)
admin = Admin(app, name='MoiSklad API Proxy', template_mode='bootstrap4')


class UserAuth(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # this names uses only for reference
    password_hash = db.Column(db.String(265))
    access_token = db.Column(db.String(265))

    def __str__(self):
        return self.name


class LogItems(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('user_auth.id'), nullable=False)
    url = db.Column(db.String(1024))
    method = db.Column(db.String(16))
    request_headers = db.Column(db.Text)
    response_headers = db.Column(db.Text)
    request_body = db.Column(db.Text)
    response_body = db.Column(db.Text)
    response_status = db.Column(db.Integer)


class UserPermissions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.Integer, db.ForeignKey('user_auth.id'), nullable=False)
    method = db.Column(db.String(16))
    url_part = db.Column(db.String(255))
    is_allowed = db.Column(db.Boolean)
    user_rel = db.relationship(UserAuth,
                               foreign_keys=[user],
                               backref='Permissions')

    def __str__(self):
        result = ''

        if self.user_rel:
            result += 'Allow '
        else:
            result += 'Disallow '

        result += '{} on {}'.format(self.method, self.url_part)

        return result


class LogView(ModelView):
    """View for admin interface to list log entries"""
    can_view_details = True
    can_create = False
    can_edit = False
    can_delete = False
    can_export = True
    column_display_pk = True
    column_list = ['id', 'user', 'url', 'method', 'response_status']


class UserView(ModelView):
    column_list = ['id', 'name', 'password_hash']


admin.add_view(UserView(UserAuth, db.session))
admin.add_view(LogView(LogItems, db.session))
admin.add_view(ModelView(UserPermissions, db.session))


def calc_permissions(user, method, path):
    disallow_permissions = UserPermissions.query.filter_by(user=user.id,
                                                           method=method,
                                                           is_allowed=False)
    for perm in disallow_permissions:
        if perm.url_part in path:
            return False

    allow_permissions = UserPermissions.query.filter_by(user=user.id,
                                                        method=method,
                                                        is_allowed=True)

    for perm in allow_permissions:
        if perm.url_part in path:
            return True

    return False


@app.route('/')
def index():
    """Index url credentials information"""
    return 'MoySklad API proxy by Petr Kuryshev <peter.kurishev@gmail.com>' + \
        ' https://github.com/peterkurishev/moisklad_proxy'


@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy(path):
    """Main proxying method"""
    response = None
    resp = None
    user = None
    excluded_req_headers = ['host', 'authorization']
    headers_dict = {name: value for (name, value) in request.headers.items()}
    if 'Authorization' in headers_dict:
        auth_type, auth_str = headers_dict['Authorization'].split(" ")
        if auth_type == 'Basic':
            user = UserAuth.query.filter_by(password_hash=auth_str).first()
        elif auth_type == 'Bearer':
            pass  # TODO: Bearer auth
        if user is None:
            error_resp = '{"errors":[{"error":"Ошибка аутентификации: Неправильный пароль или имя пользователя или ключ авторизации","code":1056,"moreInfo":"https://dev.moysklad.ru/doc/api/remap/1.2/#mojsklad-json-api-oshibki"}]}'
            return Response(error_resp, 401)
    else:
        # TODO: encode to JSON from dict
        error_resp = '{"errors":[{"error":"Ошибка аутентификации: Неправильный пароль или имя пользователя или ключ авторизации","code":1056,"moreInfo":"https://dev.moysklad.ru/doc/api/remap/1.2/#mojsklad-json-api-oshibki"}]}'
        return Response(error_resp, 401)
    log_item = LogItems(user=user.id,
                        request_headers=str(request.headers),
                        request_body=str(request.get_json() if request.get_json(silent=True) is not None else None))
    log_item.method = request.method
    log_item.url = path
    db.session.add(log_item)
    db.session.commit()
    req_headers = {
        name: value
        for (name, value) in request.headers
        if name.lower() not in excluded_req_headers
    }

    if user.access_token != None and len(user.access_token) > 0:
        # Use token for auth
        req_headers['Authorization'] = 'Bearer {}'.format(user.access_token)
    else:
        req_headers['Authorization'] = 'Basic ' + \
        b64encode(bytes("{}:{}".format(MOYSKLAD_USER, MOYSKLAD_PASSWORD),
                        'ascii')).decode('ascii')
    
    if not calc_permissions(user, request.method, path):
        return Response('Request not allowed according to proxy rules', 401)

    if request.method == 'GET':
        resp = None
        if 'entity/product?' in path:
            resp = requests.get(f'{PROXIED_API}{path}&{ONLY_FLAGGED_PRODUCTS}',
                            headers=req_headers)
        else:
            resp = requests.get(f'{PROXIED_API}{path}',
                            headers=req_headers)
        content = resp.content.decode('utf-8')
        content = content.replace(PROXIED_HOST, PROXY_HOST)
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(bytes(content, 'utf-8'), resp.status_code, headers)

    elif request.method == 'POST':
        req_data = json.loads(request.data.replace(bytes(PROXY_HOST, 'utf-8'),
                                                   bytes(PROXIED_HOST, 'utf-8')
                                                   ).decode('utf-8'))

        resp = requests.post(f'{PROXIED_API}{path}', json=req_data,
                             headers=req_headers)
        excluded_headers = ['content-encoding', 'content-length',
                                'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        resp_content = resp.content.decode('utf-8')
        resp_content = resp_content.replace('online.moysklad.ru', PROXY_HOST)
        response = Response(bytes(resp_content, 'utf-8'), resp.status_code, headers)

    elif request.method == 'DELETE':
        return Response("DELETE NOT SUPPORTED", 401)

    if resp is not None:
        log_item.response_status = resp.status_code
        log_item.response_body = resp.content.decode('utf-8')
        log_item.response_headers = str(resp.raw.headers.items())

        db.session.add(log_item)
        db.session.commit()

    return response


if __name__ == '__main__':
    app.run(debug=False, port=8883)
