#!/usr/bin/env python
import re
s = """<xml>EVENT wer<a></a>
               ASDASD
               <!CDATA<location>></xml>"""
s = re.sub("\r|\n","",s);
print s
match_list = ['EVENT.*LOCATION','bbb']
match = "|".join(match_list)
print match
p = re.compile(r"%s"%(match,),re.I|re.M)
print p.search(s)