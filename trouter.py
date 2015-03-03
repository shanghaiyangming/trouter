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
import optparse

from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from bson.code import Code
from tornado.escape import utf8, _unicode

from libs.common import ComplexEncoder,random_list,obj_hash
from conf.redis_conn import redis_client
from conf.log import logging

"""代码版本"""
version = '0.0.1'

#参数设定与检查
parser = optparse.OptionParser()

parser.add_option("-m", "--max", action="store", type="int", dest="max_conn", default=10000, help="""最大连接数""")

parser.add_option("-a", "--app", action="store", type="string", dest="app_servers", default=None, help="""app servers多台应用服务器请使用英文逗号分隔""")

parser.add_option("-p", "--port", action="store", type="int", dest="host_port", default=12345, help="""监听端口""")

parser.add_option("-t", "--threshold", action="store", type="int", dest="threshold", default=500, help="""进行操作等待的阈值""")

(options, args) = parser.parse_args()

if options.max_conn is None:
    logging.error('请设定最大连接数，默认10000')
    sys.exit(2)
else:
    max_conn = options.max_conn

if options.app_servers is None:
    logging.error('请设定应用服务器的数量')
    sys.exit(2)
else:
    app_servers = options.app_servers.split(',')

if options.host_port is None:
    logging.error('请设定监听的端口号，默认值12345')
    sys.exit(2)
else:
    host_port = options.host_port
    
if options.threshold is None:
    logging.error('请设定请求等待的阈值，低于该阈值直接转发无需等待')
    sys.exit(2)
else:
    threshold = options.threshold

host_server = "%s:%s"%(socket.gethostbyname(socket.gethostname()),host_port)
logging.info("Host:%s"%(host_server,))

class RouterHandler(tornado.web.RequestHandler):
    def initialize(self, redis_client,logging):
        self.conn_count = 0
        self.redis_client = redis_client
        self.logging = logging
        self.client = tornado.httpclient.AsyncHTTPClient()
        self.threshold = threshold
        self.pool = []
        self.security()
    
    @tornado.web.asynchronous  
    def on_response(self, response):
        if self.hash_request() in self.pool:
            self.pool.remove(self.hash_request())
        
        self.set_status(response.code)     
        if not response.error:
            self.write(response.body)
        else:
            self.logging.debug(u"%s,%s"%(response.error,response.body))
        try:
            self.finish()
        except Exception,e:
            self.logging.error(e)
        
    
    #确保列队中的请求被删除，并添加处理header信息标记
    def on_finish(self):
        if self.hash_request() in self.pool:
            self.pool.remove(self.hash_request())
        self.add_header('__PROXY__', 'Trouter %s'%(version,))
    
    @tornado.web.asynchronous
    def get(self,params):
        self.router()
            
    @tornado.web.asynchronous
    def post(self,params):
        self.router()
        
    """对来访请求进行转发处理"""
    @tornado.web.asynchronous
    def router(self):
        self.conn_count += 1
        
        #如果达到处理上限，那么停止接受连接，返回信息结束
        if self.conn_count > max_conn:
            self.set_status(500) 
            self.write('{"err":"The maximum number of connections limit is reached"}')
            return self.finish()
        
        #print self.request
        self.pool.append(self.hash_request())
        nodelay = self.get_query_argument('__NODELAY__',default=False)
        blacklist = self.get_query_argument('__BLACKLIST__',default=False)
        asynclist = self.get_query_argument('__ASYNCLIST__',default=False)
            
        
        #黑名单,直接范围503
        if blacklist:
            blacklist = blacklist.split(',')
            if self.match_list(blacklist):
                self.set_status(503)
                return self.finish()
            
        
        #对于包含这些字符的请求，自动转化为异步请求   
        if asynclist:
            asynclist = asynclist.split(',')
            if self.match_list(asynclist):
                nodelay = True
        
        if nodelay:
            self.write('{"ok":1}')
            self.finish()
        else:
            while True:
                if len(self.pool) > self.threshold:
                    time.sleep(1)
                else:
                    break 
        try:
            #同步请求方式
            #http_client = tornado.httpclient.HTTPClient()
            #response = http_client.fetch(self.construct_request(self.request))
            #self.write(response.body)
            #self.finish()
            
            #异步请求方式
            self.client.fetch(self.construct_request(self.request),callback=self.on_response)
        except Exception,e:
            self.logging.error(e)
    
    def construct_request(self, server_request):
        url = "%s://%s%s"%(self.request.protocol,str(random_list(app_servers)),self.request.uri)
        
        self.logging.info(url)
        self.logging.info(server_request)
        self.logging.info(server_request.body)
        
        if not hasattr(server_request,'body') or server_request.body=='':
            server_request.body = None

        return tornado.httpclient.HTTPRequest(
            url,
            method=server_request.method,
            headers=server_request.headers,
            body=server_request.body,
            connect_timeout = 3.0,
            request_timeout = 10.0,
            max_redirects = 5,
            allow_nonstandard_methods = True
        )
    
    #进行必要的安全检查,拦截有问题操作,考虑使用贝叶斯算法屏蔽有问题的访问
    def security(self):
        pass
    
    #在body、url、POST GET中匹配字符串,匹配,匹配的性能有待优化
    def match_list(self, match_list):
        self.logging.info(self.arguments)
        match = "|".join(match_list)
        for k,v in self.arguments:
            if re.match(match,_unicode(v)):
                return True
        return False  
    
    def hash_request(self):
        if not self.hash_request:
            self.hash_request = obj_hash(self.request)
        return self.hash_request



if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/(.*)", RouterHandler,dict(redis_client=redis_client,logging=logging))
    ],autoreload=True, xheaders=True)
    http_server = tornado.httpserver.HTTPServer(app)
    #启动多个进程完运行服务，仅在*nix有效
    #http_server.bind(host_port)
    #http_server.start(0)
    http_server.listen(host_port)
    tornado.ioloop.IOLoop.instance().start()
    



