#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
ZMQ转发设备，采用单向的streamer方式
"""
import platform
import zmq
import time
import sys
import random
import logging
import tornado

from  multiprocessing import Process
from tornado.options import define, options, parse_command_line
from tornado.httpclient import HTTPClient,AsyncHTTPClient,HTTPRequest

define("backend_port", type=int, default=55556, help="后端监听端口")
parse_command_line()

backend_port = options.backend_port
logging.info("backend_port:%d"%(backend_port,))

def http_client_worker():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://127.0.0.1:%d" % (backend_port,))
    while True:
        request = socket.recv_pyobj()
        try:
            http_client = HTTPClient()
            response = http_client.fetch(request)
            logging.info(response.code)
            if response.error:
                logging.error(response.error)
        except Exception,e:
            logging.error(e)
        finally:
            http_client.close()

if __name__ == '__main__':
    http_client_worker()