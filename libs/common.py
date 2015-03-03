#/usr/bin/python
# -*- coding: UTF-8 -*-
import json
import datetime
import random
import re
import pickle
import hashlib

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
        
def random_list(some_list):
    if len(some_list) and isinstance(some_list,list):
        random.shuffle(some_list)
        return some_list[0]
    else:
        raise ValueError,'invalid argument'
        
"""
# example:
dic = {
    "Larry Wall" : "Guido van Rossum",
    "creator" : "Benevolent Dictator for Life",
    "Perl" : "Python",
}
"""
def multiple_replace(dic, text): 
    pattern = "|".join(map(re.escape, dic.keys()))
    return re.sub(pattern, lambda m: dic[m.group()], text)

def obj_hash(obj):
    return hashlib.md5(pickle.dump(obj)).hexdigest()

    

