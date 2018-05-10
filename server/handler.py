# -*- coding: utf-8 -*-

import os
import logging
import datetime
import mimetypes
import traceback

import config


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
        data = self._raw_request.split('\r\n')
        self._method, self._uri, self._protocol = data[0].split(' ')

        uri = self._uri.split('/')
        uri.pop(0)
        self._uri = '/{}'.format('/'.join(uri))
        if self._uri.find('?') > -1:
            self._uri, params = self._uri.split('?')

            params = params.split('&')
            for param in params:
                p, v = param.split('=', 1)
                self._params[p] = v

        data.pop(0)
        while True:
            row = data.pop(0)
            if row == '':
                break

            p, v = row.split(':', 1)
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

    @property
    def protocol(self):
        return self._protocol

    @property
    def code(self):
        return self._code

    @property
    def status(self):
        return self._status

    @property
    def headers(self):
        return self._headers

    @property
    def body(self):
        return self._body

    def set_protocol(self, protocol):
        self._protocol = protocol

    def set_code(self, code):
        self._code = code

    def set_status(self, status):
        self._status = status

    def set_header(self, key, value):
        self._headers[key] = value

    def set_headers(self, headers):
        self._headers = dict(headers)

    def set_body(self, body):
        self._body = body

    def __str__(self):
        data = ['{0} {1} {2}'.format(self._protocol, self._code, self._status)]
        data.extend('{0}: {1}'.format(*head) for head in self._headers.items())
        data.append('')
        if self._body:
            data.append(self._body if isinstance(self._body, str) else str(self._body))

        return '\r\n'.join(data)


class Handler(object):
    """ Класс обработчик соединения с клиентом """

    __log_format_str = '[RESP] - {client_ip}:{client_port} "{method} {uri} {protocol}" {code} {len_response}'

    __index_page_tmpl = '\r\n'.join(('<!doctype html>', '<html>', '<head>', '<meta content="text/html; charset=utf-8">',
                                     '<title>Content of directory "{directory}"</title>', '</head>', '<body>',
                                     '<h3>Content of directory "{directory}"</h3>',
                                     '<table border="1", bordercolor="whitesmoke", cellspacing="0" cellpadding="3">', '<thead>',
                                     '<tr>', '<td>File Name</td>', '<td>Type</td>', '<td>Size</td>', '<td>Created</td>', '<td>Modified</td>',
                                     '</tr>', '</thead>', '<tbody>', '{tbody}', '</tbody>', '</table>', '</body>', '</html>'))

    __table_row_tmpl = '\r\n'.join((
        '<tr>', '<td>{file_name}</td>', '<td>{file_type}</td>', '<td>{file_size}</td>', '<td>{fcreated}</td>', '<td>{fmodified}</td>', '</tr>'))

    __error_page_tmpl = '\r\n'.join(('<!doctype html>', '<html>', '<head>', '<meta content="text/html; charset=utf-8">',
                                     '<title>{code} {title}</title>', '</head>', '<body>', '<h1>{title}</h1>', '<p>', '{error_message}',
                                     '</p>', '</body>', '</html>'))

    def __init__(self, sock, client_ip, client_port):
        self.__can_stop = False
        self.sock = sock
        self.client_ip = client_ip
        self.client_port = client_port
        self.raw_request = b''
        self.raw_response = b''
        self.request = None
        self.response = None

    def _sizeof_fmt(self, size):
        kb = 1024.0
        mb = kb * 1024.0
        gb = mb * 1024.0
        tb = gb * 1024.0
        if size <= kb:
            return str(size) + ' byte(s)'
        elif (size > kb) and (size <= mb):
            return str(round(size / kb, 2)) + ' Kb'
        elif (size > mb) and (size <= gb):
            return str(round(size / mb, 2)) + ' Mb'
        elif (size > gb) and (size <= tb):
            return str(round(size / gb, 2)) + ' Gb'
        elif size > tb:
            return str(round(size / tb, 2)) + ' Tb'
        else:
            return str(size)

    def _get_headers(self):
        return {
            'Date': datetime.datetime.today().strftime("%a, %d %b %Y %H:%M %Z"),
            'Server': 'MyServer/1.0.0',
            'Content-Length': 0,
            'Content-Type': 'text/plain',
            #'Content-Encoding': 'utf-8',
            'Connection': 'close'
        }

    def _render_directory_index(self, path):
        files = []
        folders = []
        for item in os.listdir(path):
            full_item = os.path.join(path, item)
            if os.path.isdir(full_item):
                folders.append(self.__table_row_tmpl.format(file_name='<a href={0}>{1}</a>'.format(full_item.replace(config.DOCUMENT_ROOT, ''), item),
                                                            file_type='&lt;dir&gt;', file_size='', fcreated='', fmodified=''))
            else:
                files.append(self.__table_row_tmpl.format(file_name='<a href={0}>{1}</a>'.format(full_item.replace(config.DOCUMENT_ROOT, ''), item),
                                                          file_type=mimetypes.guess_type(full_item)[0],
                                                          file_size=self._sizeof_fmt(os.path.getsize(full_item)),
                                                          fcreated=datetime.datetime.fromtimestamp(os.path.getctime(full_item)).strftime("%d.%m.%Y %H:%M:%S"),
                                                          fmodified=datetime.datetime.fromtimestamp(os.path.getmtime(full_item)).strftime("%d.%m.%Y %H:%M:%S")))

        folders.extend(files)
        return self.__index_page_tmpl.format(directory=path.replace(config.DOCUMENT_ROOT, ''), tbody='\r\n'.join(folders))

    def _wrap_error(self):
        html = self.__error_page_tmpl.format(code=self.response.code, title=self.response.status,
                                             error_message=self.response.body.replace('\r\n', '<br>').replace('\n', '<br>') if self.response.body else '')
        self.response.set_headers(self._get_headers())
        self.response.set_header('Content-Type', 'text/html')
        self.response.set_header('Content-Length', len(html))
        self.response.set_body(html)

    def _get_content_type(self, file_name):
        mime_type = mimetypes.guess_type(file_name)[0]
        return mime_type or 'application/octet-stream'

    def _create_file_response(self, method, file_name, file_data=None):
        resp = Response(self.request.protocol, 200, 'OK', headers=self._get_headers())

        if not file_data:
            with open(file_name) as f:
                file_data = f.read()

        resp.set_header('Content-Length', len(file_data))
        resp.set_header('Content-Type', self._get_content_type(file_name))
        if method == 'GET':
            resp.set_body(file_data)

        return resp

    def _create_response(self):
        if self.__can_stop:
            return None

        if not self.raw_request:
            return Response('HTTP/1.1', 400, 'Bad request')

        try:
            self.request = Request(self.raw_request)

            if self.request.method not in ('GET', 'HEAD'):
                return Response(self.request.protocol, 405, 'Method Not Allowed')

            # Действия по get-запросу (на head-запрос все то же, только блок body в response оставляем пустым):
            # 1. если адрес запроса (uri) - папка: если такой путь есть в document_root и там есть index.html - надо вернуть index.html из нее,
            # если index нет - вернуть стандартный index (рендерим свой шаблон), который будет содержать ссылки на список файлов и
            # папок папки, и ссылку на переход в папку верхнего уровня. Если такой папки нет - вернем 404.
            # 2. если uri - файл: если такой файл есть по этому пути - вернуть содержимое этого файла, при этом правильно определить и передать
            # его content-type (в т.ч. под эту логику и подпадает условие на счет file.html). Если пути uri не существует - вернуть 404.
            # Параметры запроса игнорируем (по условию задачи).
            path = '{0}{1}'.format(config.DOCUMENT_ROOT, self.request.uri)
            if os.path.exists(path):
                if os.path.isdir(path):
                    if os.path.exists(os.path.join(path, 'index.html')):
                        return self._create_file_response(self.request.method, os.path.join(path, 'index.html'))

                    # иначе рендерим свой шаблон index-a, отображающий содержимое папки, и возвращаем его
                    return self._create_file_response(self.request.method, 'index.html', file_data=self._render_directory_index(path))
                else:
                    return self._create_file_response(self.request.method, path)
            else:
                return Response(self.request.protocol, 404, 'Not Found')
        except Exception, e:
            logging.exception('Error on handle request at {0}:{1}'.format(self.client_ip, self.client_port))
            return Response('HTTP/1.1', 500, 'Internal Server Error', body=traceback.format_exc() if config.DEBUG else e)

    def _read_request(self):
        while not self.__can_stop:
            data = self.sock.recv(1024)
            self.raw_request += data
            if len(data) < 1024:
                break

    def _do_work_request(self):
        self.response = self._create_response()
        if self.response:
            # если response - ошибка, нужно вернуть страницу ошибки (рендерим свой шаблон)
            if self.response.code != 200:
                self._wrap_error()
            self.raw_response = str(self.response)
            logging.info(self.__log_format_str.format(client_ip=self.client_ip, client_port=self.client_port,
                                                      method=self.request.method if self.request else 'GET',
                                                      uri=self.request.uri if self.request else '/', protocol=self.response.protocol,
                                                      code=self.response.code, len_response=len(self.raw_response)))

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
        self._do_work_request()
        self._send_response()
        self._close()

    def stop(self):
        self.__can_stop = True
