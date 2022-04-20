#!/usr/bin/env python3

from pystalk import BeanstalkClient, BeanstalkError
from time import sleep

c = BeanstalkClient("localhost", 11300)

while True:
    try:
        job = c.reserve_job(1)
    except BeanstalkError as e:
        if e.message == 'TIMED_OUT':
            sleep(0.5)
            continue
        else:
            raise
    print("new message:")
    print(job.job_data)
    c.delete_job(job.job_id)
