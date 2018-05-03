# -*- coding: utf-8 -*-


class Response(object):
    pass

class Request(object):
    pass


class BaseHTTPServer(object):
    """ Базовый класс сервера, реализующий основную функциональность и интерфейс """
    pass


class ThreadingHTTPServer(BaseHTTPServer):
    """ Asynchronous/Thread pool server """
    pass


class ProcessingHTTPServer(BaseHTTPServer):
    """ Fork/Prefork server """
    pass


class HTTPServer(object):
    """ Оболочка над реально рабочим классом http-сервера, скрывающая реализацию threading или processing """

    def __init__(self, host, port, architect, init_handlers, max_handlers, document_root):
        self.server = None

    def start(self):
        pass

    def close(self):
        pass