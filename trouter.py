#/usr/bin/python
# -*- coding: UTF-8 -*-
"""
使用tornado进行路由转发控制，将请求通过该服务进行转发。
当短时间出现大量的请求超过阈值的情况，服务会将过载部分的请求缓存在zeroMQ中，以便能缓慢的释放请求到应用服务器。
保障服务的正常运行。

支持gearman模式调度，但是效率未必比tornao高呢
"""
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.httpclient

import os
import sys
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
import urllib

from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from bson.code import Code

from libs.common import ComplexEncoder,random_list,obj_hash,GearmanPickleClient
from conf.redis_conn import redis_client
from conf.log import logging

from tornado.escape import utf8, _unicode
from tornado.options import define, options, parse_command_line
 
"""代码版本"""
version = '0.0.1'

define("conn", type=int, default=5000, help="最大连接数")
define("apps", type=str, default="", help="app servers多台应用服务器请使用英文逗号分隔")
define("port", type=int, default=12345, help="监听端口")
define("threshold", type=int, default=500, help="进行操作等待的阈值")
define("sync_threshold", type=int, default=300, help="保障同步操作的数量")
define("gearman_srv", type=str, default="127.0.0.1:3306", help="设置Gearman服务器地址")
parse_command_line()

if options.conn is None:
    logging.error('请设定最大连接数，默认10000')
    sys.exit(2)
else:
    max_conn = options.conn

if options.apps is None:
    logging.error('请设定转发应用服务器的信息')
    sys.exit(2)
else:
    app_servers = options.apps.split(',')
    logging.info(app_servers)

if options.port is None or options.port != '':
    logging.error('请设定监听的端口号，默认值12345')
    sys.exit(2)
else:
    host_port = options.port
    
if options.threshold is None:
    logging.error('请设定请求等待的阈值，低于该阈值直接转发无需等待')
    sys.exit(2)
else:
    threshold = options.threshold
    
if options.sync_threshold is None:
    logging.error('请设定请求等待的阈值，低于该阈值直接转发无需等待')
    sys.exit(2)
else:
    sync_threshold = options.sync_threshold

gearman_srv = None  
if options.gearman_srv is not None:
    gearman_srv = options.gearman_srv.split(',')
    
if threshold <= sync_threshold:
    logging.error('阈值必须大于同步请求阈值')
    sys.exit(2)

if gearman_srv != None or gearman_srv != '':
    gearman_client = GearmanPickleClient(gearman_srv)
    
host_server = "%s:%s"%(socket.gethostbyname(socket.gethostname()),host_port)
logging.info("Host:%s"%(host_server,))
options.logging = 'info'
options.log_file_prefix = '%s%stornado_listen_%d.log'%(os.path.split(os.path.realpath(__file__))[0],os.sep,host_port)
parse_command_line()

conn_count = 0
pool = 0
sync = 0
async = 0

http_client_async = tornado.httpclient.AsyncHTTPClient(max_clients=max_conn)
http_client_sync = tornado.httpclient.AsyncHTTPClient(max_clients=max_conn)


class RouterHandler(tornado.web.RequestHandler):
    def initialize(self, redis_client,logging,http_client_sync,http_client_async):
        self.start = True
        self.redis_client = redis_client
        self.logging = logging
        self.client_sync = http_client_sync
        self.client_async = http_client_async
        self.threshold = threshold
        self.sync_threshold = sync_threshold
        self.is_async = False
        self.security()
        self.logging.info("initialize")
    
    def on_response(self, response):
        global pool,conn_count,sync,async
        pool -= 1
        if self.is_async:
            async -= 1
        self.logging.info("after response the pool number is:%d"%(pool,))
        self.logging.info("after response the async pool number is:%d"%(async,))

        if not self.is_async:
            try:
                self.set_status(response.code)   
            except Exception,e:
                self.logging.error(e)
                self.set_status(500)
            
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
        global pool,conn_count,sync,async
        conn_count -= 1
        self.add_header('__PROXY__', 'Trouter %s'%(version,))
    
    @tornado.web.asynchronous
    def get(self,params):
        self.router()
            
    @tornado.web.asynchronous
    def post(self,params):
        self.router()
        
    """对来访请求进行转发处理"""
    def router(self):
        global pool,conn_count,sync,async
        nodelay = self.get_query_argument('__NODELAY__',default=False)
        blacklist = self.get_query_argument('__BLACKLIST__',default=False)
        asynclist = self.get_query_argument('__ASYNCLIST__',default=False)
        async_result = urllib.unquote(self.get_query_argument('__ASYNC_RESULT__',default='{"ok":1}'))
        if self.start:
            conn_count += 1
        
        #黑名单,直接范围503
        if blacklist:
            blacklist = blacklist.split(',')
            if self.match_list(blacklist):
                self.set_status(503)
                self.write("503 Service Unavailable")
                return self.finish()
            
        
        #对于包含这些字符的请求，自动转化为异步请求
        async_filter = False
        if asynclist:
            asynclist = asynclist.split(',')
            if self.match_list(asynclist):
                nodelay = True
                async_filter = True
                
        if nodelay:
            if not self._finished:
                self.is_async = True
                #提交任务
                if gearman_srv!=None:
                    gearman_client.submit_job("aysnc_http_request", self.construct_request(self.request),background=True,poll_timeout=3)
                    self.write('%s'%(async_result,))
                    return self.finish()
                else:
                    self.write('%s'%(async_result,))
                    self.finish()
        
        if pool > self.threshold or (async > self.threshold - self.sync_threshold and self.is_async):
            self.start = False
            return tornado.ioloop.IOLoop.instance().add_callback(self.router)
                
        self.logging.info("pool number is %d"%(pool,))
        self.logging.info("conn number is %d"%(conn_count,))
        
        #如果达到处理上限，那么停止接受连接，返回信息结束
        if conn_count > max_conn:
            self.set_status(500) 
            self.write('{"err":"The maximum number of connections limit is reached"}')
            return self.finish()
        
        try:
            pool += 1
            if self.is_async:
                async += 1
                self.client_async.fetch(self.construct_request(self.request),callback=self.on_response)
            else:
                self.client_sync.fetch(self.construct_request(self.request),callback=self.on_response)
        except Exception,e:
            pool -= 1
            if self.is_async:
                async -= 1
            self.logging.debug(app_servers)
            self.logging.debug(self.construct_request(self.request))
            self.logging.error(e)
            self.finish()
    
    def construct_request(self, server_request):
        self.logging.info(app_servers)
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
        arguments = self.request.arguments
        if '__NODELAY__' in arguments:
            del arguments['__NODELAY__']
        if '__BLACKLIST__' in arguments:
            del arguments['__BLACKLIST__']
        if '__ASYNCLIST__' in arguments:
            del arguments['__ASYNCLIST__']
        if '__ASYNC_RESULT__' in arguments:
            del arguments['__ASYNC_RESULT__']

        match = "|".join(match_list)
        for k in arguments.keys():
            if re.match(match,_unicode(" ".join(arguments[k]))):
                return True
        if server_request.body != '' and re.match(match,_unicode(server_request.body)):
            return True
        return False  
    
    def hash_request(self):
        self.hash_request = obj_hash(self.request)
        return self.hash_request



if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/(.*)", RouterHandler,dict(
                redis_client=redis_client,
                logging=logging,
                http_client_sync=http_client_sync,
                http_client_async=http_client_async
            )
        )
    ],autoreload=True, xheaders=True, debug=True)
    
    srv = tornado.httpserver.HTTPServer(app)
    srv.listen(host_port)
    instance = tornado.ioloop.IOLoop.instance()
    instance.start()
    



