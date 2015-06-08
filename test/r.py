#!/usr/bin/env python
import re

p = re.compile(r"location|bbb",re.I|re.M)
print p.search("""<xml>
               location</xml>""")