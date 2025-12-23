# pylint: disable=C0114, C0115, C0116
from .project_model import Project
from .project_undo_manager import ProjectUndoManager


class ProjectHolder:
    def __init__(self):
        self.undo_manager = ProjectUndoManager()
        self.project = None
        self.modified = False

    def reset_project(self):
        self.project = Project()
        self.modified = False
        self.reset_undo()

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

    def set_modified(self, modified):
        self.modified = modified

    def mark_as_modified(self, modified=True, description=''):
        self.modified = modified
        if modified:
            self.add_undo(self.project.clone(), description)

    def reset_undo(self):
        self.undo_manager.reset()

    def add_undo(self, item, description=''):
        self.undo_manager.add(item, description)

    def pop_undo(self):
        return self.undo_manager.pop()

    def filled_undo(self):
        return self.undo_manager.filled()


class ProjectHandler:
    def __init__(self, project_holder):
        self.project_holder = project_holder

    def project(self):
        return self.project_holder.project

    def set_project(self, project):
        self.project_holder.set_project(project)

    def project_jobs(self):
        return self.project_holder.project_jobs()

    def num_project_jobs(self):
        return self.project_holder.num_project_jobs()

    def project_job(self, index):
        return self.project_holder.project_job(index)

    def add_job_to_project(self, job):
        self.project_holder.add_job_to_project(job)

    def modified(self):
        return self.project_holder.modified

    def set_modified(self, modified):
        self.project_holder.set_modified(modified)

    def mark_as_modified(self, modified=True, description=''):
        self.project_holder.mark_as_modified(modified, description)

    def undo_manager(self):
        return self.project_holder.undo_manager

    def reset_undo(self):
        self.project_holder.reset_undo()

    def add_undo(self, item, description=''):
        self.project_holder.add_undo(item, description)

    def pop_undo(self):
        return self.project_holder.pop_undo()

    def filled_undo(self):
        return self.project_holder.filled_undo()

    def reset_project(self):
        self.project_holder.reset_project()

    def close_project(self):
        self.reset_project()
