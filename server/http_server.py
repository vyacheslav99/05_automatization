# -*- coding: utf-8 -*-

import socket
import select
import errno


A_ASYNCHRONOUS = 'asynchronous'
A_THREADING = 'threading'
A_PROCESSING = 'processing'
SERVER_ARCHITECTURES = {
    A_ASYNCHRONOUS: 0,
    A_THREADING: 1,
    A_PROCESSING: 2
}

# Состояние обработчика:
# 0 - принято соединение/готов читать данные от клиента
# 1 - принимает данные от клиента, формирует ответ
# 2 - запрос принят, ответ сформирован, готов к отправке
# 3 - отправка ответа (отправлено частично)
# 4 - ответ отправлен, фактически соединение закрыто (отправлен сигнал shutdown)
CONN_STATE_READ_WAITING = 0
CONN_STATE_READ = 1
CONN_STATE_SEND_WAITING = 2
CONN_STATE_SEND = 3
CONN_STATE_DONE = 4

class Response(object):
    pass

class Request(object):
    pass


class Handler(object):
    """ Класс обработчик соединения с клиентом для асинхронного сервера """

    def __init__(self, sock, client_ip, client_port):
        self.sock = sock
        self.client_ip = client_ip
        self.client_port = client_port
        self.state = CONN_STATE_READ_WAITING
        self.request = b'' # Request()
        self.response = b'' # Response()

    def create_response(self):
        self.response = b'Hello, {0}!'.format(self.client_ip)

    def read(self):
        self.state = CONN_STATE_READ
        data = self.sock.recv(1024)  # будет Request.add() или что-то типа того, потом придумаю, как реализовать
        self.request += data
        if len(data) < 1024 or self.request.endswith(b'\n'):
            self.create_response()
            self.state = CONN_STATE_SEND_WAITING

    def send(self):
        self.state = CONN_STATE_SEND
        n = self.sock.send(self.response)
        if n == len(self.response):
            self.sock.shutdown(socket.SHUT_RDWR)
            self.state = CONN_STATE_DONE
        self.response = self.response[n:]

    def close(self):
        self.sock.close()


class BaseHTTPServer(object):
    """ Базовый класс сервера, определяющий интерфейс и реализующий часть основной функциональности, общую для всех потомков """

    def __init__(self, host, port, init_handlers, max_handlers, document_root):
        self.sock = None
        self.host = host
        self.port = port
        self.init_handlers = init_handlers
        self.max_handlers = max_handlers
        self.document_root = document_root

    def _init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.setblocking(0) # неблокирующий сокет (по-умолчанию он блокирующий - 1)
        self.sock.listen(5)

    def _do_serve_forever(self):
        """ Тут должен быть реализован главный цикл сервера, вызывается из метода start() после инициализации слушающего сокета """
        raise Exception('Method "_do_serve_forever" must be implemented!')

    def start(self):
        self._init_socket()
        self._do_serve_forever()

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None


class AsyncHTTPServer(BaseHTTPServer):
    """ Asynchronous server """

    def __init__(self, host, port, max_handlers, document_root):
        super(AsyncHTTPServer, self).__init__(host, port, 0, max_handlers, document_root)
        self.epoll = None
        self.connects = {}

    def _init_socket(self):
        super(AsyncHTTPServer, self)._init_socket()
        # подписываемся на события чтения, неблокирующая обработка событий сокета
        self.epoll = select.epoll()
        self.epoll.register(self.sock.fileno(), select.EPOLLIN)

    def _do_serve_forever(self):
        while True:
            # проверяем, какие произошли события, параметр "1" - время ожидания событий в сек.
            # возвращает последовательность кортежей (fileno, event_code)
            for fileno, event in self.epoll.poll(1):
                if fileno == self.sock.fileno():
                    # по слушающему сокету пришло новое соединение, принимаем его
                    try:
                        conn, addr = self.sock.accept()
                    except IOError as e:
                        if e.errno == errno.EINTR:
                            continue
                        raise

                    conn.setblocking(0)
                    if len(self.connects) == self.max_handlers:
                        # если кол-во обрабатываемых соединений достигло предела - сбрасываем
                        conn.close()
                    else:
                        # подписываем новое соединение на входящие события в epoll
                        self.epoll.register(conn.fileno(), select.EPOLLIN)
                        self.connects[conn.fileno()] = Handler(conn, addr[0], addr[1])
                elif event == select.EPOLLIN:
                    # пришли данные от клиентского соединения - нужно принять их и записать в соотв. место
                    self.connects[fileno].read()
                    if self.connects[fileno].state == CONN_STATE_SEND_WAITING:
                        # "переводим коннект в состояние приема" (точнее начинаем слушать от него событие готовности принимать данные)
                        self.epoll.modify(fileno, select.EPOLLOUT)
                elif event == select.EPOLLOUT:
                    # на клиенте произошло событие записи (т.е. он готов принимать данные - ответ от сервера)
                    self.connects[fileno].send()
                    # если отправили все - отписываем коннект от прослушивания всех типов событий
                    if self.connects[fileno].state == CONN_STATE_DONE:
                        self.epoll.modify(fileno, 0)
                elif event == select.EPOLLHUP:
                    # это событие означает, что клиент отключился - надо закрыть соединение с ним
                    self.epoll.unregister(fileno)
                    self.connects[fileno].close()
                    del connects[fileno]

    def close(self):
        if self.epoll:
            self.epoll.unregister(self.sock.fileno())
            self.epoll.close()
            self.epoll = None
        super(AsyncHTTPServer, self).close()


class ThreadingHTTPServer(BaseHTTPServer):
    """ Threading pool server """
    pass


class ProcessingHTTPServer(BaseHTTPServer):
    """ Prefork (process pool) server """
    pass


class HTTPServer(object):
    """ Оболочка над реально рабочим классом http-сервера, скрывающая реализацию threading или processing """

    def __init__(self, host, port, architect, init_handlers, max_handlers, document_root):
        self.server = None
        if architect == A_ASYNCHRONOUS:
            self.server = AsyncHTTPServer(host, port, max_handlers, document_root)
        elif architect == A_THREADING:
            self.server = ThreadingHTTPServer(host, port, init_handlers, max_handlers, document_root)
        elif architect == A_PROCESSING:
            self.server = ProcessingHTTPServer(host, port, init_handlers, max_handlers, document_root)
        else:
            raise Exception('Invalid parameter architect: {0}!'.format(architect))

    def start(self):
        self.server.start()

    def close(self):
        self.server.close()
