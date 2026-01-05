# pylint: disable=C0114, C0115, C0116, W0246
from .. common_project.project_handler import ProjectHandler


class ElementOperations(ProjectHandler):
    def __init__(self, project_holder):
        super().__init__(project_holder)

    def delete_job(self, job_index):
        if 0 <= job_index < self.num_project_jobs():
            return self.project().jobs.pop(job_index)
        return None

    def delete_action(self, job_index, action_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                return job.pop_sub_action(action_index)
        return None

    def delete_subaction(self, job_index, action_index, subaction_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if 0 <= subaction_index < len(action.sub_actions):
                    return action.pop_sub_action(subaction_index)
        return None

    def copy_job(self, job_index):
        if 0 <= job_index < self.num_project_jobs():
            return self.project_job(job_index).clone()
        return None

    def copy_action(self, job_index, action_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                return job.sub_actions[action_index].clone()
        return None

    def copy_subaction(self, job_index, action_index, subaction_index):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                if 0 <= subaction_index < len(action.sub_actions):
                    return action.sub_actions[subaction_index].clone()
        return None

    def shift_job(self, job_index, delta):
        jobs = self.project().jobs
        new_index = job_index + delta
        if 0 <= new_index < len(jobs):
            jobs.insert(new_index, jobs.pop(job_index))
            return new_index
        return job_index

    def shift_action(self, job_index, action_index, delta):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            new_index = action_index + delta
            if 0 <= new_index < len(job.sub_actions):
                job.sub_actions.insert(new_index, job.sub_actions.pop(action_index))
                return new_index
        return action_index

    def shift_subaction(self, job_index, action_index, subaction_index, delta):
        if 0 <= job_index < self.num_project_jobs():
            job = self.project_job(job_index)
            if 0 <= action_index < len(job.sub_actions):
                action = job.sub_actions[action_index]
                new_index = subaction_index + delta
                if 0 <= new_index < len(action.sub_actions):
                    action.sub_actions.insert(new_index, action.sub_actions.pop(subaction_index))
                    return new_index
        return subaction_index
