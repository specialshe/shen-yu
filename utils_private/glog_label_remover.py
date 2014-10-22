import re

rr = re.compile(r"^[IWE]\d+\s+\d+:\d+:\d+\.\d+\s+\d+\s+\w+\.(cpp|hpp):\d+\]")
#r"[IWE]\d+\s\d+:\d+:\d+\.\d+\s\s\d+\s\w+\.(hpp|cpp):\d+\]"
import sys

for line in sys.stdin:
  sys.stdout.write(rr.sub("", line))

