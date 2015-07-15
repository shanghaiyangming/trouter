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

define("backend_port", type=int, default=55556, help="后端监听端口")
define("check_mongo_load", type=int, default=0, help="是否检测mongodb负载")
define("mongo_host", type=str, default="127.0.0.1", help="mongodb主机地址")
define("mongo_port", type=int, default=27017, help="mongodb主机端口")

parse_command_line()

backend_port = options.backend_port
logging.info("backend_port:%d"%(backend_port,))

def http_client_worker():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://127.0.0.1:%d" % (backend_port,))
    while True:
        if not isMongoDBLoadGood():
            time.sleep(10)
        
        http_client = HTTPClient()
        try:
            request = socket.recv_pyobj()
            logging.info(request)
            response = http_client.fetch(request)
            logging.info(response.code)
            if response.error:
                logging.error(response.error)
        except Exception,e:
            logging.error(e)
        finally:
            http_client.close()

def isMongoDBLoadGood():
    if options.check_mongo_load==1:
        if random.randint(0,9)==1:
            waitingForLockNumber = 0
            client = MongoClient(options.mongo_host, options.mongo_port)
            db = client[database]
            ops = db.current_op()
            for op in ops[u'inprog']:
                if op.has_key(u'ns') and op[u'ns'] not in exclude:
                    if op.has_key(u'waitingForLock') and op[u'waitingForLock']:
                        waitingForLockNumber += 1
            if waitingForLockNumber > 30:
                return False
    return True
        


if __name__ == '__main__':
    http_client_worker()