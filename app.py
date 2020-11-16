'''Moi sklad proxy to control the permissions'''
from flask import Flask,request,redirect,Response
import requests

app = Flask(__name__)
PROXIED_API = 'https://online.moysklad.ru'

@app.route('/')
def index():
    return 'Flask is running!'

@app.route('/<path:path>',methods=['GET','POST','DELETE'])
def proxy(path):
    '''Main proxying method'''
    response = None
    if request.method=='GET':
        resp = requests.get(f'{PROXIED_API}{path}')
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)

    elif request.method=='POST':
        resp = requests.post(f'{PROXIED_API}{path}',json=request.get_json())
        excluded_headers = ['content-encoding', 'content-length',
                            'transfer-encoding', 'connection']
        headers = [(name, value) for (name, value) in resp.raw.headers.items()
                   if name.lower() not in excluded_headers]
        response = Response(resp.content, resp.status_code, headers)

    elif request.method=='DELETE':
        resp = requests.delete(f'{PROXIED_API}{path}').content
        response = Response(resp.content, resp.status_code, headers)

    return response

if __name__ == '__main__':
    app.run(debug = False,port=80)
