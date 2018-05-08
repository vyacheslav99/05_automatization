# -*- coding: utf-8 -*-

import logging
import datetime


class Request(object):

    def __init__(self, request_str):
        self._raw_request = request_str
        self._method = None
        self._uri = None
        self._protocol = None
        self._params = {}
        self._headers = {}
        self._body = None
        self._parse_request_str()

    def _parse_request_str(self):
        data = self._raw_request.split()
        self._method, self._uri, self._protocol = data[0].split(' ')

        uri = self._uri.split('/')
        uri.pop(0)
        self._uri = '/{}'.format('/'.join(uri))
        self._uri, params = self._uri.split('?')

        params = params.split('&')
        for param in params:
            p, v = param.split('=')
            self._params[p] = v

        while True:
            row = data.pop(0)
            if row == '':
                break

            p, v = row.split(':')
            self._headers[p.strip()] = v.strip()

        self._body = '\r\n'.join(data)

    @property
    def method(self):
        return self._method

    @property
    def uri(self):
        return self._uri

    @property
    def protocol(self):
        return self._protocol

    @property
    def host(self):
        return self._headers.get('Host', None)

    @property
    def params(self):
        return self._params

    @property
    def headers(self):
        return self._headers

    @property
    def body(self):
        return self._body


class Response(object):

    def __init__(self, protocol, code, status, headers=None, body=None):
        self._protocol = protocol
        self._code = code
        self._status = status
        self._headers = headers or {}
        self._body = body

    def set_protocol(self, protocol):
        self._protocol = protocol

    def set_code(self, code):
        self._code = code

    def set_status(self, status):
        self._status = status

    def set_header(self, key, value):
        self._headers[key] = value

    def set_body(self, body):
        self._body = body

    def __str__(self):
        data = ['{0} {1} {2}'.format(self._protocol, self._code, self._status)]
        data.extend('{0}: {1}'.format(*head) for head in self._headers)
        data.append('')
        if self._body:
            data.append(self._body if isinstance(self._body, str) else str(self._body))

        return '\r\n'.join(data)


class Handler(object):
    """ Класс обработчик соединения с клиентом """

    def __init__(self, sock, client_ip, client_port):
        self.__can_stop = False
        self.sock = sock
        self.client_ip = client_ip
        self.client_port = client_port
        self.raw_request = b''
        self.raw_response = b''
        self.request = None
        self.response = None

    def _get_headers(self):
        return {
            'Date': datetime.datetime.today().strftime("%a, %d %b %Y %H:%M %Z"),
            'Server': 'MyServer/1.0.0',
            'Content‑Length': 0,
            'Content‑Type': 'text/plain; charset=utf-8',
            'Connection': 'close'
        }

    def _create_response(self):
        if self.__can_stop:
            return

        if not self.raw_request:
            self.response = Response('HTTP/1.1', 400, 'Bad request')
        else:
            try:
                self.request = Request(self.raw_request)

                if self.request.method not in ('GET', 'HEAD'):
                    self.response = Response(self.request.protocol, 405, 'Method Not Allowed')
            except Exception, e:
                self.response = Response('HTTP/1.1', 500, 'Internal Server Error', body=e)

        self.raw_response = str(self.response)

    def _read_request(self):
        while not self.__can_stop:
            data = self.sock.recv(1024)
            self.raw_request += data
            if len(data) < 1024:
                break

    def _send_response(self):
        while not self.__can_stop:
            n = self.sock.send(self.raw_response)
            if n == len(self.raw_response):
                break
            self.raw_response = self.raw_response[n:]

    def _close(self):
        self.sock.close()
        self.sock = None

    def handle_request(self):
        self._read_request()
        self._create_response()
        self._send_response()
        self._close()

    def stop(self):
        self.__can_stop = True
