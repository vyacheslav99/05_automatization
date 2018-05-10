# -*- coding: utf-8 -*-

import socket
import errno
import logging
import threading

from handler import Handler, Response


class Worker(object):

    def __init__(self, index):
        self.id = index
        self.__thread = None
        self._reset()
        self.init_thread()

    def _reset(self):
        self.__stopped = True
        self.__handler = None
        self.sock = None
        self.client_ip = None
        self.client_port = None

    def _do_process(self):
        logging.info('[{0}] Accepted connection on {1}:{2}'.format(self.id, self.client_ip, self.client_port))
        self.__stopped = False
        self.__ready = False

        try:
            self.__handler = Handler(self.sock, self.client_ip, self.client_port)
            self.__handler.handle_request()
        finally:
            logging.info('[{0}] Stopped connection on {1}:{2}'.format(self.id, self.client_ip, self.client_port))
            self._reset()

    def init_thread(self):
        self.__thread = threading.Thread(target=self._do_process)
        self.__thread.setDaemon(1)
        self.__ready = True

    def accept(self, sock, client_ip, client_port):
        if not self.is_free():
            raise Exception('Worker {0} not ready to accept connections!'.format(self.id))

        self.sock = sock
        self.client_ip = client_ip
        self.client_port = client_port

    def start(self):
        self.__thread.start()

    def stop(self):
        if self.__handler:
            self.__handler.stop()

        if self.__thread and self.__thread.isAlive():
            self.__thread.join()

        self.__thread = None

    def is_free(self):
        return self.__stopped

    def is_ready(self):
        return self.__ready


class HTTPServer(object):

    def __init__(self, host, port, init_handlers=0, max_handlers=0):
        self.active = False
        self.sock = None
        self.host = host
        self.port = port
        self.init_handlers = init_handlers
        self.max_handlers = max_handlers
        self.wrk_pool = []
        self.wrk_svc_thread = None

    def _init_socket(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        #self.sock.setblocking(0)
        self.sock.listen(5)
        self.sock.settimeout(1)
        logging.info('Started listening on {0}:{1}'.format(self.host, self.port))

    def _start_wrk_service(self):
        self.wrk_svc_thread = threading.Thread(target=self._do_wrk_service)
        self.wrk_svc_thread.setDaemon(1)
        self.wrk_svc_thread.start()

    def _init_workers(self):
        for i in xrange(self.init_handlers):
            self.wrk_pool.append(Worker(i))

    def _get_worker(self):
        for wrk in self.wrk_pool:
            if wrk.is_ready():
                return wrk

        if len(self.wrk_pool) < self.max_handlers:
            self.wrk_pool.append(Worker(len(self.wrk_pool) - 1))
            return self.wrk_pool[-1]

        return None

    def _check_workers(self):
        for wrk in self.wrk_pool:
            if not self.active:
                break

            if wrk.is_free() and not wrk.is_ready():
                wrk.stop()
                wrk.init_thread()

    def _accept_connection(self, sock, client_ip, client_port):
        worker = self._get_worker()

        if worker is None:
            sock.close()
            logging.info('Reset connection on {0}:{1}: limit connections exceeded'.format(client_ip, client_port))
        else:
            worker.accept(sock, client_ip, client_port)
            worker.start()

    def _do_wrk_service(self):
        # выполняется в отдельном потоке!
        while self.active:
            try:
                self._check_workers()
            except Exception:
                logging.exception('Error at service workers!')

    def _do_serve_forever(self):
        while self.active:
            try:
                conn, addr = self.sock.accept()
            except socket.timeout:
                continue
            except IOError as e:
                if e.errno == errno.EINTR:
                    continue
                raise

            try:
                conn.setblocking(0)
                self._accept_connection(conn, *addr)
                # возврат завершившихся workers в пул вынесем в отдельный поток
                # self._check_workers()
            except Exception:
                logging.exception('Error on handle connection at {0}:{1}!'.format(*addr))

    def start(self):
        try:
            self.active = True
            self._init_workers()
            self._start_wrk_service()
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

        if self.wrk_svc_thread and self.wrk_svc_thread.isAlive():
            self.wrk_svc_thread.join()

        for wrk in self.wrk_pool:
            wrk.stop()
