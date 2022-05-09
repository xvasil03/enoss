#!/usr/bin/env python3

from greenstalk import Client

c = Client(("localhost", 11300))

print("beanstalkd-stats:")
print(c.stats())
while True:
    print("Reserving message")
    job = c.reserve()
    print("new message:")
    print(job.body)
    c.delete(job)
c.close()
