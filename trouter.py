#/usr/bin/python
# -*- coding: UTF-8 -*-
"""
使用tornado进行路由转发控制，将请求通过该服务进行转发。
当短时间出现大量的请求超过阈值的情况，服务会将过载部分的请求缓存在zeroMQ中，以便能缓慢的释放请求到应用服务器。
保障服务的正常运行。
"""
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient

import urllib
import json
import datetime
import time
import re
import urlparse
import hashlib
import time
import json
import redis
import pickle

from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from bson.code import Code

from ..libs.common import ComplexEncoder
from ..conf.redis import redis_client
from ..conf.log import logging

threshold = 500
conn_count = 0
domain_list = ['scrm.umaman.com']
app_servers = ['10.0.0.10','10.0.0.11','10.0.0.12','10.0.0.13']

class RouterHandler(tornado.web.RequestHandler):
    
    def initialize(self, redis_client):
        self.redis_client = redis_client
        self.client = tornado.httpclient.AsyncHTTPClient()
        self.threshold = 500
        self.pool = []
        self.security()
        
    def on_response(self, response):
        self.pool.remove()
        #self.write("on_getuserinfo error:%s"%(response.body,))
        self.finish()
    
    
    @tornado.web.asynchronous
    def get(self):
        self.pool.append(self.hash_request())
        if len(self.pool) <= self.threshold:
            self.client.fetch(self.request,self.on_response)
        else:
            pass
            
    @tornado.web.asynchronous
    def post(self):
        self.request.url = self.filter_url(self.request.url)
        self.client.fetch(self.request,self.on_response)
        
    def filter_url(self, url):
        if isinstance(url,basestring):
            url.replace()
        else:
            return url
    
    
    """"进行必要的安全检查,拦截有问题操作"""
    def security(self):
        pass
    
    def hash_request(self):
        if not self.hash_request:
            return hashlib.md5().update(pickle.dump(self.request)).hexdigest()
        
        
    
    
    


if __name__ == "__main__":
    from tornado.options import define, options
    define("port", default=8000, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    app = tornado.web.Application([
        (r"/(.*)", RouterHandler,dict(redis_client=redis_client,log=logging))
    ],autoreload=True, xheaders=True)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()



