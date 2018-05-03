# -*- coding: utf-8 -*-

import logging
import argparse

import config
from http_server import HTTPServer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", "-p", type=int, action="store", default=config.PORT)
    ap.add_argument("--workers", "-w", type=int, action="store", default=config.INIT_HANDLERS)
    ap.add_argument("--doc_root", "-r", type=str, action="store", default=config.DOCUMENT_ROOT)
    args = ap.parse_args()

    logging.basicConfig(**config.LOGGING)

    try:
        server = HTTPServer("localhost", args.port, config.ARCHITECT, config.INIT_HANDLERS,
                            config.MAX_HANDLERS, config.DOCUMENT_ROOT)
        logging.info("Starting server at %s" % args.port)
        server.start()
    except KeyboardInterrupt:
        pass
    finally:
        server.close()
    logging.info("Server stopped")

if __name__ == '__main__':
    main()