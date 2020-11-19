'''Moi sklad proxy to control the permissions'''
import requests
from flask import Flask, request, Response

app = Flask(__name__)
PROXIED_API = 'https://online.moysklad.ru/'


@app.route('/')
def index():
    '''Index url credentials information'''
    return 'MoySklad API proxy by Petr Kuryshev'


@app.route('/<path:path>', methods=['GET', 'POST', 'DELETE'])
def proxy(path):
    '''Main proxying method'''
    response = None
    # import pdb; pdb.set_trace()
    if request.method == 'GET':
        resp = requests.get(f'{PROXIED_API}{path}')
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)

    elif request.method == 'POST':
        excluded_req_headers = ['host']
        req_headers = {name: value for (name, value) in request.headers
                   if name.lower() not in excluded_req_headers}
        resp = requests.post(f'{PROXIED_API}{path}', json=request.get_json(),
                             headers=req_headers)
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)

    elif request.method == 'DELETE':
        resp = requests.delete(f'{PROXIED_API}{path}').content
        response = Response(resp.content, resp.status_code, headers)

    return response


if __name__ == '__main__':
    app.run(debug=False, port=8883)
