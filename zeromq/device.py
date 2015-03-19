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

from tornado.options import define, options, parse_command_line

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

if __name__ == '__main__':
    zmq_device()

