# -*- coding: utf-8 -*-

import logging
import argparse

import config
from http_server import HTTPServer


class Handler(object):
    """ Класс обработчик соединения с клиентом """

    def __init__(self, sock, client_ip, client_port):
        self.__can_stop = False
        self.sock = sock
        self.client_ip = client_ip
        self.client_port = client_port
        self.request = b''
        self.response = b''

    def _create_response(self):
        self.response = b'Hello, {0}!'.format(self.client_ip)

    def _read(self):
        while not self.__can_stop:
            data = self.sock.recv(1024)
            self.request += data
            if len(data) < 1024: # or self.request.endswith(b'\n'):
                break

    def _send(self):
        while not self.__can_stop:
            n = self.sock.send(self.response)
            if n == len(self.response):
                break
            self.response = self.response[n:]

    def _close(self):
        self.sock.close()
        self.sock = None

    def start(self):
        self._read()
        if not self.__can_stop:
            self._create_response()
        self._send()
        self._close()

    def stop(self):
        self.__can_stop = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", "-p", type=int, action="store", default=config.PORT)
    ap.add_argument("--workers", "-w", type=int, action="store", default=config.INIT_HANDLERS)
    ap.add_argument("--doc_root", "-r", type=str, action="store", default=config.DOCUMENT_ROOT)
    args = ap.parse_args()

    logging.basicConfig(**config.LOGGING)
    server = HTTPServer("127.0.0.1", args.port, Handler, args.workers, config.MAX_HANDLERS, args.doc_root)

    logging.info("Starting server...")
    server.start()
    logging.info("Server stopped")

if __name__ == '__main__':
    main()
