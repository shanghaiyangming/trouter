#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
ZMQ转发设备，采用单向的streamer方式
"""
from tornado.httpclient import AsyncHTTPClient
from  multiprocessing import Process

