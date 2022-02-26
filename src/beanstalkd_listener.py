#!/usr/bin/env python3

from pystalkd.Beanstalkd import Connection
from time import sleep
import json
import pprint

c = Connection("localhost", 11300)

while True:
    job = c.reserve(0)
    if not job:
        sleep(0.5)
        continue
    print("new job:")
    parsed = json.loads(job.body)
    pprint.pprint(parsed)
    print("\n\n")
    job.delete()
