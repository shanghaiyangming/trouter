#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
该worker的目的是为了统计可能存在风险的请求数据
"""
import platform
import zmq
import time
import sys
import random
import logging
import tornado
import pickle
from collections import Counter

define("server_ip", type=int, default="127.0.0.1", help="服务器IP")
define("backend_port", type=int, default=55558, help="后端监听端口")
parse_command_line()

server_ip = options.server_ip
backend_port = options.backend_port
logging.info("backend_port:%d"%(backend_port,))

session_counter = Counter()



def security_worker():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://%s:%d" % (server_ip,backend_port))
    while True:
        try:
            obj = socket.recv_pyobj()
            
        except Exception,e:
            logging.error(e)
        finally:
            pass

if __name__ == '__main__':
    security_worker()