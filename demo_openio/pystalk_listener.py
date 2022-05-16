#!/usr/bin/env python3

from greenstalk import Client

c = Client(("127.0.0.41", 6014))
c.watch("enoss")

print("beanstalkd-stats:")
print(c.stats_tube("enoss"))
while True:
    print("Reserving message")
    job = c.reserve()
    print("new message:")
    print(job.body)
    c.delete(job)
c.close()
