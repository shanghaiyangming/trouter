#/usr/bin/python
# -*- coding: UTF-8 -*-
import tornado
import urllib
from tornado.httpclient import AsyncHTTPClient
from multiprocessing import Process

max_loop = 10
def handle_request(response):
    if response.error:
        print "Error:", response.error
    else:
        print response.body

http_client = AsyncHTTPClient(max_clients=max_loop)
for i in xrange(0,max_loop):
    print i
    try:
        url = "http://urm.umaman.com/tag/index/mark?identifyId=yangming&ext={%22username%22:%22ben%22,%22age%22:%2223%22}&suiji="
        url = "%s%d"%(url,i)
        print url
        data = {'tags':[u'宅男',u'文青']}
        request = tornado.httpclient.HTTPRequest(
            url,
            method = 'POST',
            body = urllib.urlencode(data),
            follow_redirects  = True,
            max_redirects = 30,
            connect_timeout = 300,
            request_timeout = 300,
            allow_nonstandard_methods = True
        )
        http_client.fetch(request, handle_request)
    except Exception,e:
        print e

tornado.ioloop.IOLoop.instance().start()
        