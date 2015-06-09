#/usr/bin/python
# -*- coding: UTF-8 -*-
"""
使用tornado进行路由转发控制，将请求通过该服务进行转发。
当短时间出现大量的请求超过阈值的情况，服务会将过载部分的请求缓存在zeroMQ中，以便能缓慢的释放请求到应用服务器。
保障服务的正常运行。

版本、扩展与依赖：
python 2.6+
tornado4.1
pymongo2.8
redis(暂未使用)
zmq

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
import platform
import zmq

from pymongo import MongoClient
from bson.objectid import ObjectId
from pymongo import ASCENDING, DESCENDING
from bson.code import Code

from libs.common import ComplexEncoder,random_list,obj_hash
from conf.redis_conn import redis_client
from conf.log import logging

from tornado.escape import utf8, _unicode
from tornado.options import define, options, parse_command_line
from tornado.httpclient import AsyncHTTPClient
from tornado.httputil import HTTPHeaders

#from collections import Counter
 
"""代码版本"""
version = '0.6'

define("conn", type=int, default=5000, help="最大连接数")
define("apps", type=str, default="", help="app servers多台应用服务器请使用英文逗号分隔")
define("port", type=int, default=12345, help="监听端口")
define("threshold", type=int, default=500, help="进行操作等待的阈值")
define("sync_threshold", type=int, default=300, help="保障同步操作的数量")
define("request_timeout", type=int, default=300, help="客户端请求最大超时时间，默认300秒")
define("enable_zmq", type=int, default=0, help="开启ZeroMQ模式,0为关闭1为开启")
define("zmq_device", type=str, default="", help="zmq device服务地址,tcp://127.0.0.1:55555")
define("security_device", type=str, default="", help="security device服务地址,tcp://127.0.0.1:55557")
parse_command_line()

request_timeout = float(options.request_timeout)
enable_zmq = options.enable_zmq
zmq_device = options.zmq_device
security_device = options.security_device

if options.conn is None:
    logging.error('请设定最大连接数，默认5000')
    sys.exit(2)
else:
    max_conn = options.conn

if options.apps is None:
    logging.error('请设定转发应用服务器的信息')
    sys.exit(2)
else:
    app_servers = options.apps.split(',')
    logging.info(app_servers)

if options.port is None or options.port is '':
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
    
if threshold < sync_threshold:
    logging.error('阈值必须大于同步请求阈值')
    sys.exit(2)
    
host_server = "%s:%s"%(socket.gethostbyname(socket.gethostname()),host_port)
logging.info("Host:%s"%(host_server,))
options.logging = 'info'
options.log_file_prefix = '%s%stornado_listen_%d.log'%(os.path.split(os.path.realpath(__file__))[0],os.sep,host_port)
parse_command_line()

conn_count = 0
pool = 0
sync = 0
async = 0

if platform.system() != 'Windows':
    #采用curl的方式进行处理，速度更快，兼容性更好
    AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient")
    
http_client_async = AsyncHTTPClient(max_clients=3*threshold)
http_client_sync = AsyncHTTPClient(max_clients=3*threshold)

#如果设置了zeroMQ那么连接zeroMQ服务器
if enable_zmq > 0 and zmq_device != '':
    context = zmq.Context()
    zmq_socket = context.socket(zmq.PUSH)
    zmq_socket.connect(zmq_device)
    
#如果设置了zeroMQ security_device 那么连接zeroMQ security_device服务器
if security_device != '':
    context = zmq.Context()
    security_socket = context.socket(zmq.PUSH)
    security_socket.connect(security_device)

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
        self.retry_times = 3
    
    def set_headers(self, response):
        global pool,conn_count,sync,async
        try:
            if isinstance(response.headers,HTTPHeaders):
                self.logging.info("headers type is HTTPHeaders")
                headers = response.headers.get_all()

            elif isinstance(response.headers,dict):
                self.logging.info("headers type is dict")
                headers = response.headers
            else:
                self.logging.debug(response.headers)
                headers = []
                
            for k,v in headers:
                if k!='Transfer-Encoding':
                    self.logging.info("%s:%s"%(k,v))
                    self.set_header(k,_unicode(v))
            
            #添加trouter信息，便于debug
            self.set_header('script_execute_time','%d ms'%(1000*(time.time()-self.timer),))
            self.set_header('trouter','version:%s,current pool:%d,current conn count:%d'%(version,pool,conn_count))
        except Exception,e:
            self.logging.error(e)
    
    
    def on_response(self, response):
        global pool,conn_count,sync,async
        pool -= 1
        if self.is_async:
            async -= 1
        self.logging.info("after response the pool number is:%d"%(pool,))
        self.logging.info("after response the async pool number is:%d"%(async,))
        self.logging.info("response code:%d"%(response.code,))
        self.logging.info(response)
        
        #检测到599，重试3次
        if response.error and response.code==599:
            self.logging.debug(response) 
            if self.retry_times > 0:
                self.logging.info('retry limit is %d'%(self.retry_times,))
                self.retry_times -= 1
                return tornado.ioloop.IOLoop.instance().add_callback(self.router)
            else:
                self.logging.info('retry limit is 0')
                #重试结束后
                try:
                    self.finish()
                except Exception,e:
                    self.logging.error(e)
                return False

        if not self.is_async:
            try:
                self.set_status(response.code)   
            except Exception,e:
                self.logging.error(e)
                self.set_status(500)
            
            self.set_headers(response)

            if not response.error or response.body !='':
                self.logging.info("response.body execute")
                self.write(response.body)
            else:
                self.logging.error(u"%s,%s"%(response.error,response.body))
            
            try:
                self.finish()
            except Exception,e:
                self.logging.error(e)
        
    
    #确保列队中的请求被删除，并添加处理header信息标记
    def on_finish(self):
        global pool,conn_count,sync,async
        if self.start:
            conn_count -= 1
            self.start = False
            self.logging.info("conn number is:%d"%(conn_count,))
        
    #Called at the beginning of a request before  `get`/`post`/etc
    @tornado.web.asynchronous
    def prepare(self):
        global conn_count
        conn_count += 1
        self.logging.info("conn number is %d"%(conn_count,))
    
    @tornado.web.asynchronous
    def get(self,params):
        self.router()
            
    @tornado.web.asynchronous
    def post(self,params):
        self.router()
        
    """对来访请求进行转发处理"""
    def router(self):
        global pool,conn_count,sync,async
        nodelay = self.request.headers.get('__NODELAY__', False)
        if not nodelay:
            nodelay = self.get_query_argument('__NODELAY__',default=False)
        
        blacklist = self.request.headers.get('__BLACKLIST__', False)
        if not blacklist:
            blacklist = self.get_query_argument('__BLACKLIST__',default=False)
            
        asynclist = self.request.headers.get('__ASYNCLIST__', False)
        if not asynclist:
            asynclist = self.get_query_argument('__ASYNCLIST__',default=False)
        
        async_result = self.request.headers.get('__ASYNC_RESULT__',default=False)
        if not async_result:
            async_result = self.get_query_argument('__ASYNC_RESULT__',default='{"ok":1}')
        
        content_type = self.request.headers.get('__CONTENT_TYPE__',default='')
        if not content_type:
            content_type = self.get_query_argument('__CONTENT_TYPE__',default='')
        
        jsonp_callback_varname = self.request.headers.get('__JSONP_CALLBACK_VARNAME__',default='jsonpcallback')
        if not jsonp_callback_varname:
            jsonp_callback_varname = self.get_query_argument('__JSONP_CALLBACK_VARNAME__',default='jsonpcallback')
            
        jsonpcallback = self.get_query_argument('%s'%(jsonp_callback_varname,),default='')
        
        
        #如果代码进行了urlencode编码，则自动进行解码
        if isinstance(blacklist, basestring):
            blacklist = urllib.unquote(blacklist)
        if isinstance(asynclist, basestring):
            asynclist = urllib.unquote(asynclist)
        if isinstance(async_result, basestring):
            async_result = urllib.unquote(async_result)

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
                self.logging.info("enable aysnc list")
                nodelay = True
                async_filter = True
            
                
        #开启debug模式时关闭异步操作    
        enable_debug_mode = self.get_query_argument('__ENABLE_DEBUG__',default=False)
        if enable_debug_mode:
            nodelay = False
                
        if nodelay:
            if not self._finished:
                self.is_async = True
                self.set_status(200)
                
                #默认判断，对于json格式的处理，默认jsonpcallback兼容jquery调用方法，如需定制请在__JSONP_CALLBACK_VARNAME__指定
                if(self.is_json(async_result)):
                    self.set_header('Content-Type','text/javascript')
                    if jsonpcallback!='':
                        self.write('%s(%s)'%(jsonpcallback,async_result))
                    else:
                        self.write('%s'%(async_result,))
                else:
                    self.write('%s'%(async_result,))
                
                #可以强行执行content-type  
                if(content_type!=''):
                    self.set_header('Content-Type',content_type)
                
                self.finish()
                
                #如果设置了zeroMQ队列的话，放到zmq列队中结束请求
                if enable_zmq > 0 and zmq_device != '':
                    self.logging.info("zmq_socket send_pyobj")
                    return zmq_socket.send_pyobj(self.construct_request(self.request,True))
        
        if pool > self.threshold or (async > self.threshold - self.sync_threshold and self.is_async):
            self.start = False
            return tornado.ioloop.IOLoop.instance().add_callback(self.router)
                
        self.logging.info("pool number is %d"%(pool,))
        self.logging.info("conn number is %d"%(conn_count,))
        
        #如果达到处理上限，那么停止接受连接，返回信息结束
        if conn_count > max_conn:
            self.set_status(500)
            self.logging.error("The maximum number of connections limit is reached")
            self.write('{"err":"The maximum number of connections limit is reached"}')
            return self.finish()
        
        # 后台转发脚本计算时间开始
        self.timer = time.time()
        try:
            self.logging.debug(self.request)
            request = self.construct_request(self.request)
            self.logging.debug(request)
            pool += 1
            if self.is_async:
                async += 1
                self.client_async.fetch(request,callback=self.on_response)
            else:
                self.client_sync.fetch(request,callback=self.on_response)
        except Exception,e:
            pool -= 1
            if self.is_async:
                async -= 1
            self.logging.debug(app_servers)
            self.logging.debug(self.construct_request(self.request))
            self.logging.error(e)
            self.finish()
    
    def construct_request(self, server_request,is_pickle = False):
        self.logging.info(app_servers)
        url = "%s://%s%s"%(self.request.protocol,str(random_list(app_servers)),self.request.uri)
        self.logging.info(url)
        if not hasattr(server_request,'body') or server_request.body=='':
            server_request.body = None
        
        self.logging.debug(server_request)
        
        if is_pickle:
            dict_headers = {}
            for k,v in server_request.headers.get_all():
                dict_headers[k] = v
            server_request.headers = dict_headers
            self.logging.info(server_request.headers)
        
        if server_request.body == None and server_request.method=='POST':
            server_request.method = 'GET'
            
        return tornado.httpclient.HTTPRequest(
            url,
            method=server_request.method,
            headers=server_request.headers,
            body=server_request.body,
            follow_redirects = False,#不自动执行重定向，返回给用户浏览器处理
            request_timeout = request_timeout,
            allow_nonstandard_methods = True
        )
    
    #进行必要的安全检查,拦截有问题操作,考虑使用贝叶斯算法屏蔽有问题的访问
    def security(self):
        return False
        if security_device != '':
            session_id = self.get_cookie('PHPSESSID', '')
            remote_ip = self.request.headers.get('X-Real-Ip', self.request.remote_ip)
            user_agent = self.request.headers.get('User-Agent', '')
            request_uri = self.request.uri
            http_host = self.request.headers.get('Host', '')
            
            security_info = {}
            security_info['http_host'] = http_host
            security_info['request_uri'] = request_uri
            security_info['session_id'] = session_id
            security_info['remore_ip'] = remote_ip
            security_info['user_agent'] = user_agent
            self.logging.info("security_info:%s"%(str(security_info)))
            security_socket.send_pyobj(security_info)
        else:
            self.logging.info("turn off security features")
        return True
    
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
        if '__ENABLE_DEBUG__' in arguments:
            del arguments['__ENABLE_DEBUG__']
        if '__CONTENT_TYPE__' in arguments:
            del arguments['__CONTENT_TYPE__']
        if '__JSONP_CALLBACK_VARNAME__' in arguments:
            del arguments['__JSONP_CALLBACK_VARNAME__']
            
        match = "|".join(match_list)
        self.logging.info(match)
        p = re.compile(r'%s'%(match,),re.I|re.M)
        for k in arguments.keys():
            arguments_string = _unicode(" ".join(arguments[k]))
            arguments_string = re.sub("\r|\n","",arguments_string)
            if p.search(arguments_string):
                return True
        
        if hasattr(self.request,'body'):
            self.logging.info(_unicode(self.request.body))
            body = re.sub("\r|\n","",_unicode(self.request.body))
            if p.search(body):
                return True
        
        return False
    
    #判断字符串是否为有效的json字符串
    def is_json(self,json_str):
        try:
            json_object = json.loads(json_str)
        except ValueError,e:
            return False
        else:
            return True



if __name__ == "__main__":
    app = tornado.web.Application([
        (r"/(.*)", RouterHandler,dict(
                redis_client=redis_client,
                logging=logging,
                http_client_sync=http_client_sync,
                http_client_async=http_client_async
            )
        )
    ],autoreload=True, xheaders=True)
    
    srv = tornado.httpserver.HTTPServer(app)
    srv.listen(host_port)
    instance = tornado.ioloop.IOLoop.instance()
    instance.start()
    



