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
from  multiprocessing import Process


http_async_client = AsyncHTTPClient(max_clients=100)

def zmq_device(frontend_port,backend_port):
    try:
        context = zmq.Context(1)
        # Socket facing clients
        frontend = context.socket(zmq.PULL)
        frontend.bind("tcp://*:%d"%(frontend_port,))
        
        # Socket facing services
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
        
def on_response(response):
    if response.error:
        logging.error(response.error)
    else:
        logging.info(response.code)
       
def http_client_worker():
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect("tcp://127.0.0.1:%d" % backend_port)
    
    while True:
        request = socket.recv_pyobj()
        try:
            http_async_client.fetch(request,callback=on_response)
        except Exception,e:
            logging.error(e)
        

if __name__ == "__main__":
    Process(target=zmq_device, args=(5555,5556)).start()
    for work_num in range(10):
        Process(target=worker, args=(work_num,)).start()
