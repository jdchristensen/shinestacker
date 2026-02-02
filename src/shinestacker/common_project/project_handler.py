# pylint: disable=C0114, C0115, C0116, R0904, R0917, R0913
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

    def mark_as_modified(self, modified=True):
        self.modified = modified

    def mark_as_not_modified(self):
        self.modified = False

    def save_prev_undo_state(self, pre_state, description='', action_type='',
                             old_position=None, new_position=None):
        self.mark_as_modified()
        self.add_undo(pre_state, description, action_type, old_position, new_position)

    def save_undo_state(self, description='', action_type='',
                        old_position=None, new_position=None):
        self.save_prev_undo_state(self.project.clone(), description, action_type,
                                  old_position, new_position)

    def reset_undo(self):
        self.undo_manager.reset()

    def add_undo(self, item, description='', action_type=None,
                 old_position=None, new_position=None):
        self.undo_manager.add(item, description, action_type, old_position, new_position)

    def pop_undo(self):
        return self.undo_manager.pop()

    def filled_undo(self):
        return self.undo_manager.filled()

    def undo(self):
        if self.filled_undo():
            current_state = self.project.clone()
            entry = self.pop_undo()
            new_entry = {
                'item': current_state,
                'description': entry['description'],
                'action_type': entry.get('action_type', ''),
                'old_position': entry.get('new_position', (-1, -1, -1)),
                'new_position': entry.get('old_position', (-1, -1, -1))
            }
            if 'modern_widget_state' in entry:
                new_entry['modern_widget_state'] = entry['modern_widget_state']
            self.undo_manager.add_to_redo(new_entry)
            self.set_project(entry['item'])
            return entry
        return None

    def pop_redo(self):
        return self.undo_manager.pop_redo()

    def filled_redo(self):
        return self.undo_manager.filled_redo()

    def redo(self):
        if self.filled_redo():
            current_state = self.project.clone()
            entry = self.pop_redo()
            # Entry from redo buffer has swapped positions from when it was created during undo
            # Swap them back to create the correct entry for undo buffer
            new_entry = {
                'item': current_state,
                'description': entry['description'],
                'action_type': entry.get('action_type', ''),
                # Swap back: entry has old=new, new=old, so we swap to get old=old, new=new
                'old_position': entry.get('new_position', (-1, -1, -1)),
                'new_position': entry.get('old_position', (-1, -1, -1))
            }
            if 'modern_widget_state' in entry:
                new_entry['modern_widget_state'] = entry['modern_widget_state']
            self.undo_manager.add_to_undo(new_entry)
            self.set_project(entry['item'])
            # Return entry with positions swapped back for the view
            # View expects: old_position = before redo, new_position = after redo
            return_entry = {
                'item': entry['item'],
                'description': entry['description'],
                'action_type': entry.get('action_type', ''),
                'old_position': entry.get('new_position', (-1, -1, -1)),  # Swap back
                'new_position': entry.get('old_position', (-1, -1, -1))   # Swap back
            }
            if 'modern_widget_state' in entry:
                return_entry['modern_widget_state'] = entry['modern_widget_state']
            return return_entry
        return None

    def set_copy_buffer(self, item):
        self.copy_buffer = item.clone()

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

    def is_valid_job_index(self, index):
        return 0 <= index < self.num_project_jobs()

    def project_job(self, index):
        return self.project_holder.project_job(index) if self.is_valid_job_index(index) else None

    def is_valid_index_in(self, a, index):
        return False if a is None else 0 <= index < len(a.sub_actions)

    def project_action(self, job_index, action_index):
        job = self.project_job(job_index)
        if job is None:
            return None
        return job.sub_actions[action_index] \
            if self.is_valid_index_in(job, action_index) else None

    def project_subaction(self, job_index, action_index, subaction_index):
        action = self.project_action(job_index, action_index)
        if action is None:
            return None
        return action.sub_actions[subaction_index] \
            if self.is_valid_index_in(action, subaction_index) else None

    def project_element(self, job_index, action_index=-1, subaction_index=-1):
        if job_index < 0:
            return None
        if action_index < 0:
            return self.project_job(job_index)
        if subaction_index < 0:
            return self.project_action(job_index, action_index)
        return self.project_subaction(job_index, action_index, subaction_index)

    def project_container(self, job_index=-1, action_index=-1):
        if job_index < 0:
            return self.project().jobs
        if action_index < 0:
            return self.project_job(job_index).sub_actions
        return self.project_action(job_index, action_index).sub_actions

    def valid_indices(self, job_index, action_index=-1, subaction_index=-1):
        job = self.project_job(job_index)
        if job is None:
            return False
        if action_index == -1:
            return True
        if not self.is_valid_index_in(job, action_index):
            return False
        if subaction_index == -1:
            return True
        action = job.sub_actions[action_index]
        return self.is_valid_index_in(action, subaction_index)

    def add_job_to_project(self, job):
        self.project_holder.add_job_to_project(job)

    def modified(self):
        return self.project_holder.modified

    def set_modified(self, modified):
        self.project_holder.set_modified(modified)

    def mark_as_not_modified(self):
        self.project_holder.mark_as_not_modified()

    def save_undo_state(self, description='', action_type='',
                        old_position=None, new_position=None):
        self.project_holder.save_undo_state(description, action_type,
                                            old_position, new_position)

    def save_prev_undo_state(self, pre_state, description='', action_type='',
                             old_position=None, new_position=None):
        self.project_holder.save_prev_undo_state(pre_state, description, action_type,
                                                 old_position, new_position)

    def undo_manager(self):
        return self.project_holder.undo_manager

    def reset_undo(self):
        self.project_holder.reset_undo()

    def add_undo(self, item, description='', action_type=None,
                 old_position=None, new_position=None):
        self.project_holder.add_undo(item, description, action_type, old_position, new_position)

    def pop_undo(self):
        return self.project_holder.pop_undo()

    def filled_undo(self):
        return self.project_holder.filled_undo()

    def undo(self):
        return self.project_holder.undo()

    def pop_redo(self):
        return self.project_holder.pop_redo()

    def filled_redo(self):
        return self.project_holder.filled_redo()

    def redo(self):
        return self.project_holder.redo()

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
        self.mark_as_not_modified()
        self.reset_undo()
        return abs_file_path

    def do_save(self, file_path):
        json_obj = jsonpickle.encode({
            'project': self.project().to_dict(),
            'version': CURRENT_PROJECT_FILE_VERSION
        })
        with open(file_path, 'w', encoding="utf-8") as f:
            f.write(json_obj)
        self.mark_as_not_modified()
