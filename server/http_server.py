# -*- coding: utf-8 -*-

import socket
import errno
import logging
import threading


class Handler(object):
    """ Класс обработчик соединения с клиентом """

    def __init__(self, sock, client_ip, client_port):
        self.sock = sock
        self.client_ip = client_ip
        self.client_port = client_port
        self.request = b''
        self.response = b''

    def _create_response(self):
        self.response = b'Hello, {0}!'.format(self.client_ip)

    def _read(self):
        pass
        # data = self.sock.recv(1024)
        # self.request += data
        # if len(data) < 1024 or self.request.endswith(b'\n'):
        #     self.create_response()

    def _send(self):
        pass
        # n = self.sock.send(self.response)
        # if n == len(self.response):
        #     self.sock.shutdown(socket.SHUT_RDWR)
        # self.response = self.response[n:]

    def _close(self):
        self.sock.close()


class HTTPServer(object):

    def __init__(self, host, port, init_handlers=0, max_handlers=0, document_root=None):
        self.active = False
        self.sock = None
        self.host = host
        self.port = port
        self.init_handlers = init_handlers
        self.max_handlers = max_handlers
        self.document_root = document_root
        self.handlers = {}

    def _init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(0) # неблокирующий сокет (по-умолчанию он блокирующий - 1)
        self.sock.listen(5)
        logging.info('Started listening on {0}:{1}'.format(self.host, self.port))

    def _handle_connection(self, sock, client_ip, client_port):
        obj = Handler(sock, client_ip, client_port)

    def _do_serve_forever(self):
        while self.active:
            try:
                conn, addr = self.sock.accept()
            except IOError as e:
                if e.errno == errno.EINTR:
                    continue
                raise

            conn.setblocking(0)
            if self.max_handlers > 0 and len(self.handlers) >= self.max_handlers:
                conn.close()
                logging.info('Reset connection on {0}:{1}: limit connections exceeded'.format(*addr))
            else:
                self.handlers[conn.fileno()] = threading.Thread(target=self._handle_connection, args=(conn,) + addr)
                self.handlers[conn.fileno()].start()
                logging.info('Accepted connection on {0}:{1}'.format(*addr))

    def start(self):
        try:
            self.active = True
            self._init_socket()
            self._do_serve_forever()
        except KeyboardInterrupt:
            logging.info('KeyboardInterrupt')
        except Exception, e:
            logging.exception("Unexpected error: %s" % e)
        finally:
            self._close()

    def stop(self):
        self.active = False

    def _close(self):
        logging.info('Stop listen on {0}:{1}'.format(self.host, self.port))
        if self.sock:
            self.sock.close()
            self.sock = None
        self.active = False  # на всякий случай
