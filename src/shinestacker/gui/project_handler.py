# pylint: disable=C0114, C0115, C0116
from .project_undo_manager import ProjectUndoManager


class ProjectHandler:
    def __init__(self):
        self.undo_manager = ProjectUndoManager()
        self.project = None

    def set_project(self, project):
        self.project = project

    def project_jobs(self):
        return self.project.jobs

    def num_project_jobs(self):
        return len(self.project.jobs)

    def project_job(self, index):
        return self.project.jobs[index]

    def add_job_to_project(self, job):
        self.project.jobs.append(job)

    def reset_undo(self):
        self.undo_manager.reset()

    def add_undo(self, item, description=''):
        self.undo_manager.add(item, description)

    def pop_undo(self):
        return self.undo_manager.pop()

    def filled_undo(self):
        return self.undo_manager.filled()
