# -*- coding: utf-8 -*-

import logging
import argparse

import config
from http_server import HTTPServer
from handler import Handler


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
