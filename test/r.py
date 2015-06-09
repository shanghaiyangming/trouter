#!/usr/bin/env python
import re
s = """<xml>EVENT 
               ASDASD
               location</xml>"""
s = re.sub("\r|\n","",s);
print s
match_list = "EVENT.*location,bbb"
match = "|".join(match_list)
p = re.compile(r"()|()",re.I|re.M)
print p.search(s)