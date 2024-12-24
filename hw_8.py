from http.server import BaseHTTPRequestHandler, HTTPServer
import os
from requests import get, put
import urllib.parse
import json

YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/resources"
YANDEX_DISK_BACKUP_PATH = "Backup"
YANDEX_DISK_TOKEN = ""


def run(handler_class=BaseHTTPRequestHandler):
    server_address = ('', 8000)
    httpd = HTTPServer(server_address, handler_class)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()


class HttpGetHandler(BaseHTTPRequestHandler):
    uploaded_files = set()

    @classmethod
    def get_uploaded_files_from_yandex(cls):
        headers = {"Authorization": YANDEX_DISK_TOKEN}
        url = f"{YANDEX_DISK_API_URL}?path={YANDEX_DISK_BACKUP_PATH}"
        resp = get(url, headers=headers)

        if resp.status_code == 200:
            items = json.loads(resp.text).get("_embedded", {}).get("items", [])
            cls.uploaded_files = set(item["name"]
                                     for item in items if item["type"] == "file")
        else:
            print(
                f"Error getting list from Yandex Disk: {resp.status_code} {resp.text}")
            cls.uploaded_files = set()

    def do_GET(self):
        HttpGetHandler.get_uploaded_files_from_yandex()

        def fname2html(fname):
            style = "background-color: rgba(0, 200, 0, 0.25); pointer-events:none; margin-top: 8px;" if fname in HttpGetHandler.uploaded_files else "cursor: pointer; margin-top: 8px;"
            return f"""
                <li style="{style}" onclick="fetch('/upload', {{'method': 'POST', 'body': '{fname}'}})">
                    {fname}
                </li>
            """

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("""
            <html>
                <head>
                </head>
                <body>
                    <ul>
                      {files}
                    </ul>
                </body>
            </html>
        """.format(files="\n".join(map(fname2html, os.listdir("pdfs")))).encode())

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        fname = self.rfile.read(content_len).decode("utf-8")
        local_path = f"pdfs/{fname}"
        ya_path = f"{YANDEX_DISK_BACKUP_PATH}/{urllib.parse.quote(fname)}"
        resp = get(f"https://cloud-api.yandex.net/v1/disk/resources/upload?path={ya_path}",
                   headers={"Authorization": YANDEX_DISK_TOKEN})
        print(resp.text)
        upload_url = json.loads(resp.text)["href"]
        print(upload_url)
        resp = put(upload_url, files={'file': (fname, open(local_path, 'rb'))})
        print(resp.status_code)

        if resp.status_code == 201:
            HttpGetHandler.get_uploaded_files_from_yandex()
        self.send_response(200)
        self.end_headers()


if __name__ == '__main__':
    YANDEX_DISK_TOKEN = f"OAuth {input('Токен с Яндекс Полигона: ')}"
    run(handler_class=HttpGetHandler)
