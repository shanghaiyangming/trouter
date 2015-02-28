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
import socket

from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from bson.code import Code

from libs.common import ComplexEncoder,random_list,obj_hash
from conf.redis_conn import redis_client
from conf.log import logging

max_conn = 10000
domain_list = ['scrm.umaman.com']
app_servers = ['10.0.0.10:9000','10.0.0.11:9000','10.0.0.12:9000','10.0.0.13:9000']
host_port = 8000
host_server = "%s:%s"%(socket.gethostbyname(socket.gethostname()),host_port)
logging.info("Host:%s"%(host,))

class RouterHandler(tornado.web.RequestHandler):
    
    def initialize(self, redis_client,logging):
        self.conn_count = 0
        self.redis_client = redis_client
        self.logging = logging
        self.client = tornado.httpclient.AsyncHTTPClient()
        self.threshold = self.get_query_argument('__THRESHOLD__',default=500) 
        self.pool = []
        self.security()
        
    def on_response(self, response):
        self.pool.remove(self.hash_request())
        if not response.error:
            self.write(response.body)
            self.finish()
        else:
            self.logging.debug(u"%s,%s"%(response.error,response.body))
            self.finish()
    
    
    @tornado.web.asynchronous
    def get(self):
        self.router()
            
    @tornado.web.asynchronous
    def post(self):
        self.router()
        
    """对来访请求进行转发处理"""
    def router(self):
        self.conn_count += 1
        
        #如果达到处理上限，那么停止接受连接，返回信息结束
        if self.conn_count > max_conn:
            self.set_status(500) 
            self.write('{"err":"The maximum number of connections limit is reached"}')
            self.finish()
        
        self.request.url = self.filter_url(self.request.url)
        self.pool.append(self.hash_request())
        nodelay = self.get_query_argument('__NODELAY__',default=False)
        block_content = self.get_query_argument('__BLOCK_CONTENT__',default=False)
        app_servers = self.get_query_argument('__APP_SERVERS__',default=False)
        if app_servers:
            app_servers.split(',')
            
        
        #未来考虑增加过滤功能
        if block_content:
            block_list = block_content.split(',')
        
        if nodelay:
            self.write('{"ok":1}')
            self.finish()
        else:
            while True:
                if len(self.pool) > self.threshold:
                    time.sleep(1)
                else:
                    break
        self.client.fetch(self.request,self.on_response)
        
        
    def filter_url(self, url):
        if isinstance(url,basestring):
            return url.replace(host,str(random_list(app_servers)))
        else:
            return url
    
    
    #进行必要的安全检查,拦截有问题操作,考虑使用贝叶斯算法屏蔽有问题的访问
    def security(self):
        pass
    
    def hash_request(self):
        if not self.hash_request:
            self.hash_request = obj_hash(self.request)
        return self.hash_request



if __name__ == "__main__":
    from tornado.options import define, options
    define("port", default=host_port, help="run on the given port", type=int)
    tornado.options.parse_command_line()
    app = tornado.web.Application([
        (r"/(.*)", RouterHandler,dict(redis_client=redis_client,logging=logging))
    ],autoreload=True, xheaders=True)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
    



