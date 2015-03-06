#!/usr/bin/env python
import gearman
def check_request_status(job_request):
    if job_request.complete:
        print "Job %s finished!  Result: %s - %s" % (job_request.job.unique, job_request.state, job_request.result)
    elif job_request.timed_out:
        print "Job %s timed out!" % job_request.unique
    elif job_request.state == JOB_UNKNOWN:
        print "Job %s connection failed!" % job_request.unique


gm_client = gearman.GearmanClient(['192.168.5.41:4730'])
completed_job_request = gm_client.submit_job("task_name", "arbitrary binary data",background=True,poll_timeout=3)
check_request_status(completed_job_request)