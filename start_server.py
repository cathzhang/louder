#!/usr/bin/env python3
"""多线程 HTTP 服务器，支持 Range 请求（音频 seek 必需）"""
import os
import re
import socketserver
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8000
ROOT = str(Path(__file__).resolve().parent)

BYTE_RANGE_RE = re.compile(r'bytes=(\d+)-(\d+)?$')

def parse_byte_range(byte_range):
    if byte_range.strip() == '':
        return None, None
    m = BYTE_RANGE_RE.match(byte_range)
    if not m:
        raise ValueError('Invalid byte range')
    first, last = [x and int(x) for x in m.groups()]
    if last and last < first:
        raise ValueError('Invalid byte range')
    return first, last

def copy_byte_range(infile, outfile, start=None, stop=None, bufsize=16*1024):
    if start is not None:
        infile.seek(start)
    while 1:
        to_read = min(bufsize, stop + 1 - infile.tell() if stop else bufsize)
        buf = infile.read(to_read)
        if not buf:
            break
        outfile.write(buf)

class RangeHandler(SimpleHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def send_head(self):
        if 'Range' not in self.headers:
            self.range = None
            return SimpleHTTPRequestHandler.send_head(self)
        try:
            self.range = parse_byte_range(self.headers['Range'])
        except ValueError:
            self.send_error(400, 'Invalid byte range')
            return None
        first, last = self.range

        path = self.translate_path(self.path)
        f = None
        ctype = self.guess_type(path)
        try:
            f = open(path, 'rb')
        except OSError:
            self.send_error(404, 'File not found')
            return None

        fs = os.fstat(f.fileno())
        file_len = fs[6]
        if first >= file_len:
            self.send_error(416, 'Requested Range Not Satisfiable')
            return None

        if last is None or last >= file_len:
            last = file_len - 1
        response_length = last - first + 1

        self.send_response(206)
        self.send_header('Content-type', ctype)
        self.send_header('Content-Range', 'bytes %s-%s/%s' % (first, last, file_len))
        self.send_header('Content-Length', str(response_length))
        self.send_header('Last-Modified', self.date_time_string(fs.st_mtime))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()
        return f

    def copyfile(self, source, outputfile):
        if not getattr(self, 'range', None):
            return SimpleHTTPRequestHandler.copyfile(self, source, outputfile)
        start, stop = self.range
        copy_byte_range(source, outputfile, start, stop)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


def main():
    os.chdir(ROOT)

    with ThreadingHTTPServer(("", PORT), RangeHandler) as httpd:
        print("=" * 50)
        print("  多线程 Range 服务器已启动")
        print(f"  打开: http://localhost:{PORT}/web/")
        print("=" * 50)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")


if __name__ == "__main__":
    main()
