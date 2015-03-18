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
from  multiprocessing import Process
from tornado.options import define, options, parse_command_line
from tornado.httpclient import HTTPClient,AsyncHTTPClient

define("frontend_port", type=int, default=55555, help="前端监听端口")
define("backend_port", type=int, default=55556, help="后端监听端口")
parse_command_line()

frontend_port = options.frontend_port
backend_port = options.backend_port
logging.info("frontend_port:%d"%(frontend_port,))
logging.info("backend_port:%d"%(backend_port,))

def zmq_device():
    try:
        context = zmq.Context(1)
        frontend = context.socket(zmq.PULL)
        frontend.bind("tcp://*:%d"%(frontend_port,))
        
        backend = context.socket(zmq.PUSH)
        backend.bind("tcp://*:%d"%(backend_port,))

        zmq.device(zmq.STREAMER, frontend, backend)
    except Exception, e:
        logging.error(e)
        logging.error("bringing down zmq device")
    finally:
        frontend.close()
        backend.close()
        context.term()
      
def http_client_worker():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://127.0.0.1:%d" % (backend_port,))
    http_client = HTTPClient()
    while True:
        request = socket.recv_pyobj()
        try:
            response = http_client.fetch(request)
            logging.info(response.code)
            if response.error:
                logging.error(response.error)
        except Exception,e:
            logging.error(e)

if __name__ == '__main__':
    Process(target=zmq_device).start()
    for work_num in xrange(100):
        Process(target=http_client_worker).start()
