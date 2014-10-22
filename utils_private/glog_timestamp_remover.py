import re

rr = re.compile(r"[IWE]\d+\s+\d+:\d+:\d+\.\d+\s+\d+\s+")

import sys

for line in sys.stdin:
  sys.stdout.write(rr.sub("", line))

