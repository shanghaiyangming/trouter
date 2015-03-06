#!/usr/bin/env python
import gearman
class CustomGearmanWorker(gearman.GearmanWorker):
    def on_job_execute(self, current_job):
        print "Job started"
        return super(CustomGearmanWorker, self).on_job_execute(current_job)

    def on_job_exception(self, current_job, exc_info):
        print "Job failed, CAN stop last gasp GEARMAN_COMMAND_WORK_FAIL"
        return super(CustomGearmanWorker, self).on_job_exception(current_job, exc_info)

    def on_job_complete(self, current_job, job_result):
        print "Job failed, CAN stop last gasp GEARMAN_COMMAND_WORK_FAIL"
        return super(CustomGearmanWorker, self).send_job_complete(current_job, job_result)

    def after_poll(self, any_activity):
        # Return True if you want to continue polling, replaces callback_fxn
        return True

def task_callback(gearman_worker, job):
    return job.data

new_worker = CustomGearmanWorker(['192.168.5.41:4730'])
new_worker.register_task("echo", task_callback)
new_worker.work()