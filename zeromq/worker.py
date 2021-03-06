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
import pickle

from multiprocessing import Process
from tornado.options import define, options, parse_command_line
from tornado.httpclient import HTTPClient,AsyncHTTPClient,HTTPRequest
from tornado.httputil import HTTPHeaders,HTTPServerRequest
from tornado.httpserver import HTTPRequest
from tornado.escape import utf8, _unicode

define("backend_port", type=int, default=55556, help="后端监听端口")
parse_command_line()

backend_port = options.backend_port
logging.info("backend_port:%d"%(backend_port,))

def sleep(diff_time):
    diff_time = int(diff_time)
    logging.info("diff time is %d"%(diff_time,))
    if diff_time >= 15:
        logging.info("sleep 120s")
        time.sleep(120)
    elif diff_time >= 10:
        logging.info("sleep 60s")
        time.sleep(60)
    elif diff_time >= 5:
        logging.info("sleep 30s")
        time.sleep(30)
    elif diff_time >= 3:
        logging.info("sleep 10s")
        time.sleep(10)
    else:
        pass
    return True

def http_client_worker():
    diff_time = 0
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://127.0.0.1:%d" % (backend_port,))
    while True:
        sleep(diff_time)
        start_time = time.time()
        http_client = HTTPClient()
        try:
            request = socket.recv_pyobj()
            response = http_client.fetch(request)
            if response.error:
                logging.error(response.error)
        except Exception,e:
            logging.error(e)
        finally:
            http_client.close()
        
        end_time = time.time()
        diff_time = end_time - start_time
        logging.info("url:%s\n host:%s\n body:%s\n response_code:%d\n start_time:%d end_time:%d diff_time:%d"%(request.url,request.headers['Host'],_unicode(request.body),response.code,start_time,end_time,diff_time))

if __name__ == '__main__':
    http_client_worker()