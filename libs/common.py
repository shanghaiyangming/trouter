#/usr/bin/python
# -*- coding: UTF-8 -*-
import datetime

class ComplexEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        elif isinstance(obj, object):
            return str(obj)
        else:
            return json.JSONEncoder.default(self, obj)
        
