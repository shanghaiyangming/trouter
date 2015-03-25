#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import tornado
from  multiprocessing import Process
from tornado.httpclient import AsyncHTTPClient

repeat = 5

def handle_response(response):
    global repeat
    repeat -= 1
    if response.error:
        print "err:%s"%(response.error,)
    else:
        print response.body
    if repeat==0:
        tornado.ioloop.IOLoop.instance().stop()
    


def test(client_id):
    for i in xrange(repeat):
        url = "http://urmdemo.umaman.com/weixinredpack/index/get?activity_id=55067db6479619010a80fed5&customer_id=55067d8c4996193a3a8b4f49&re_openid=yangming_%d&redpack_id=55067da0479619680980ff62"%(client_id,)
        request = tornado.httpclient.HTTPRequest(
            url,
            method='GET',
            connect_timeout = 60,
            request_timeout = 300
        )
        
        client = AsyncHTTPClient()
        client.fetch(request,handle_response)
    tornado.ioloop.IOLoop.instance().start()
    


for i in xrange(5):
    Process(target=test).start()
    
    