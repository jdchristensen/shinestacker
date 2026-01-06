# pylint: disable=C0114, C0115, C0116, R0904
import os
import json
import jsonpickle
from .. core.exceptions import InvalidProjectError
from .. gui.project_model import Project


class ProjectHolder:
    def __init__(self, undo_manager):
        self.undo_manager = undo_manager
        self.project = None
        self.modified = False
        self.copy_buffer = None
        self.current_file_path = ''

    def reset_project(self):
        self.project = Project()
        self.modified = False
        self.current_file_path = ''
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

    def mark_as_modified(self, modified=True, description='', action_type=None,
                         affected_position=(-1, -1, -1)):
        self.modified = modified
        if modified:
            self.add_undo(self.project.clone(), description, action_type, affected_position)

    def save_undo_state(self, pre_state, description='', action_type='',
                        affected_position=(-1, -1, -1)):
        self.modified = True
        self.add_undo(pre_state, description, action_type, affected_position)

    def reset_undo(self):
        self.undo_manager.reset()

    def add_undo(self, item, description='', action_type=None, affected_position=(-1, -1, -1)):
        self.undo_manager.add(item, description, action_type, affected_position)

    def pop_undo(self):
        return self.undo_manager.pop()

    def filled_undo(self):
        return self.undo_manager.filled()

    def undo(self):
        if self.filled_undo():
            entry = self.pop_undo()
            self.set_project(entry['item'])
            return entry
        return None

    def set_copy_buffer(self, item):
        self.copy_buffer = item

    def has_copy_buffer(self):
        return self.copy_buffer is not None

    def current_file_directory(self):
        if os.path.isdir(self.current_file_path):
            return self.current_file_path
        return os.path.dirname(self.current_file_path)

    def current_file_name(self):
        if os.path.isfile(self.current_file_path):
            return os.path.basename(self.current_file_path)
        return ''

    def set_current_file_path(self, path):
        if path and not os.path.exists(path):
            raise RuntimeError(f"Path: {path} does not exist.")
        self.current_file_path = os.path.abspath(path)
        os.chdir(self.current_file_directory())


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

    def is_valid_job_index(self, index):
        return 0 <= index < self.num_project_jobs()

    def modified(self):
        return self.project_holder.modified

    def set_modified(self, modified):
        self.project_holder.set_modified(modified)

    def mark_as_modified(self, modified=True, description='', action_type=None,
                         affected_position=(-1, -1, -1)):
        self.project_holder.mark_as_modified(modified, description, action_type, affected_position)

    def save_undo_state(self, pre_state, description='', action_type='',
                        affected_position=(-1, -1, -1)):
        self.project_holder.save_undo_state(pre_state, description, action_type, affected_position)

    def undo_manager(self):
        return self.project_holder.undo_manager

    def reset_undo(self):
        self.project_holder.reset_undo()

    def add_undo(self, item, description='', action_type=None, affected_position=(-1, -1, -1)):
        self.project_holder.add_undo(item, description, action_type, affected_position)

    def pop_undo(self):
        return self.project_holder.pop_undo()

    def filled_undo(self):
        return self.project_holder.filled_undo()

    def undo(self):
        return self.project_holder.undo()

    def reset_project(self):
        self.project_holder.reset_project()

    def copy_buffer(self):
        return self.project_holder.copy_buffer

    def set_copy_buffer(self, item):
        self.project_holder.set_copy_buffer(item)

    def has_copy_buffer(self):
        return self.project_holder.has_copy_buffer()

    def current_file_path(self):
        return self.project_holder.current_file_path

    def current_file_directory(self):
        return self.project_holder.current_file_directory()

    def current_file_name(self):
        return self.project_holder.current_file_name()

    def set_current_file_path(self, path):
        self.project_holder.set_current_file_path(path)


CURRENT_PROJECT_FILE_VERSION = 1


class ProjectIOHandler(ProjectHandler):
    def open_project(self, file_path):
        abs_file_path = os.path.abspath(file_path)
        with open(abs_file_path, 'r', encoding="utf-8") as file:
            json_obj = json.load(file)
        project = Project.from_dict(json_obj['project'], json_obj['version'])
        if project is None:
            raise InvalidProjectError(file_path)
        self.set_project(project)
        self.set_current_file_path(file_path)
        self.mark_as_modified(False)
        self.reset_undo()
        return abs_file_path

    def do_save(self, file_path):
        json_obj = jsonpickle.encode({
            'project': self.project().to_dict(),
            'version': CURRENT_PROJECT_FILE_VERSION
        })
        with open(file_path, 'w', encoding="utf-8") as f:
            f.write(json_obj)
        self.mark_as_modified(False)
