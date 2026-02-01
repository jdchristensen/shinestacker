import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from shinestacker.core.exceptions import InvalidProjectError
from shinestacker.gui.project_model import Project
from shinestacker.common_project.project_handler import (
    ProjectHandler, ProjectHolder, ProjectIOHandler)


class TestProjectHolder(unittest.TestCase):
    def setUp(self):
        self.undo_manager = Mock()
        self.holder = ProjectHolder(self.undo_manager)
        self.test_project = Project()
        self.test_project.jobs = [Mock(), Mock()]

    def test_init(self):
        self.assertIsNone(self.holder.project)
        self.assertFalse(self.holder.modified)
        self.assertIsNone(self.holder.copy_buffer)
        self.assertEqual(self.holder.current_file_path, '')

    def test_reset_project(self):
        self.holder.project = self.test_project
        self.holder.modified = True
        self.holder.current_file_path = '/path'
        self.holder.reset_undo = Mock()
        self.holder.reset_project()
        self.assertIsInstance(self.holder.project, Project)
        self.assertFalse(self.holder.modified)
        self.assertEqual(self.holder.current_file_path, '')
        self.holder.reset_undo.assert_called_once()

    def test_set_project(self):
        self.holder.set_project(self.test_project)
        self.assertEqual(self.holder.project, self.test_project)

    def test_project_jobs(self):
        self.holder.project = self.test_project
        self.assertEqual(self.holder.project_jobs(), self.test_project.jobs)

    def test_num_project_jobs(self):
        self.holder.project = self.test_project
        self.assertEqual(self.holder.num_project_jobs(), 2)

    def test_project_job(self):
        self.holder.project = self.test_project
        self.assertEqual(self.holder.project_job(0), self.test_project.jobs[0])

    def test_add_job_to_project(self):
        self.holder.project = Project()
        job = Mock()
        self.holder.add_job_to_project(job)
        self.assertEqual(self.holder.project.jobs, [job])

    def test_set_modified(self):
        self.holder.set_modified(True)
        self.assertTrue(self.holder.modified)

    def test_mark_as_not_modified(self):
        self.holder.mark_as_not_modified()
        self.assertFalse(self.holder.modified)

    def test_save_undo_state(self):
        pre_state = Mock()
        self.holder.add_undo = Mock()
        self.holder.save_undo_state(pre_state, 'test', 'move', (0,), (1,))
        self.assertTrue(self.holder.modified)
        self.holder.add_undo.assert_called_once()

    def test_reset_undo(self):
        self.holder.reset_undo()
        self.undo_manager.reset.assert_called_once()

    def test_add_undo(self):
        item = Mock()
        self.holder.add_undo(item, 'test', 'delete', (0,), (1,))
        self.undo_manager.add.assert_called_once()

    def test_pop_undo(self):
        self.undo_manager.pop.return_value = 'entry'
        result = self.holder.pop_undo()
        self.assertEqual(result, 'entry')

    def test_filled_undo(self):
        self.undo_manager.filled.return_value = True
        self.assertTrue(self.holder.filled_undo())

    def test_undo(self):
        self.undo_manager.filled.return_value = True
        entry = {
            'item': Mock(), 'description': 'test', 'action_type': 'add',
            'old_position': (0,), 'new_position': (1,)}
        self.undo_manager.pop.return_value = entry
        self.holder.project = Mock()
        self.holder.project.clone.return_value = 'current_state'
        self.undo_manager.add_to_redo = Mock()
        result = self.holder.undo()
        self.assertEqual(result, entry)

    def test_pop_redo(self):
        self.undo_manager.pop_redo.return_value = 'entry'
        self.assertEqual(self.holder.pop_redo(), 'entry')

    def test_filled_redo(self):
        self.undo_manager.filled_redo.return_value = True
        self.assertTrue(self.holder.filled_redo())

    def test_redo(self):
        self.undo_manager.filled_redo.return_value = True
        entry = {
            'item': Mock(), 'description': 'test', 'action_type': 'add',
            'old_position': (0,), 'new_position': (1,)}
        self.undo_manager.pop_redo.return_value = entry
        self.holder.project = Mock()
        self.holder.project.clone.return_value = 'current_state'
        self.undo_manager.add_to_undo = Mock()
        result = self.holder.redo()
        self.assertIn('item', result)

    def test_set_copy_buffer(self):
        item = Mock()
        item.clone.return_value = 'cloned'
        self.holder.set_copy_buffer(item)
        self.assertEqual(self.holder.copy_buffer, 'cloned')

    def test_has_copy_buffer(self):
        self.assertFalse(self.holder.has_copy_buffer())
        self.holder.copy_buffer = Mock()
        self.assertTrue(self.holder.has_copy_buffer())

    def test_current_file_directory_file(self):
        self.holder.current_file_path = '/path/to/file.txt'
        self.assertEqual(self.holder.current_file_directory(), '/path/to')

    def test_current_file_directory_dir(self):
        self.holder.current_file_path = '/path/to/'
        self.assertEqual(self.holder.current_file_directory(), '/path/to')

    def test_current_file_name(self):
        with patch('os.path.isfile', return_value=True):
            self.holder.current_file_path = '/path/to/file.txt'
            self.assertEqual(self.holder.current_file_name(), 'file.txt')

    def test_set_current_file_path(self):
        with tempfile.NamedTemporaryFile() as tmp:
            self.holder.set_current_file_path(tmp.name)
            self.assertEqual(self.holder.current_file_path, os.path.abspath(tmp.name))

    def test_set_current_file_path_invalid(self):
        with self.assertRaises(RuntimeError):
            self.holder.set_current_file_path('/invalid/path')


class TestProjectHandler(unittest.TestCase):
    def setUp(self):
        self.holder = Mock()
        self.handler = ProjectHandler(self.holder)
        self.test_project = Project()
        self.test_project.jobs = [Mock(), Mock()]

    def test_project(self):
        self.holder.project = self.test_project
        self.assertEqual(self.handler.project(), self.test_project)

    def test_set_project(self):
        self.handler.set_project(self.test_project)
        self.holder.set_project.assert_called_with(self.test_project)

    def test_project_jobs(self):
        self.holder.project_jobs.return_value = [1, 2]
        self.assertEqual(self.handler.project_jobs(), [1, 2])

    def test_num_project_jobs(self):
        self.holder.num_project_jobs.return_value = 5
        self.assertEqual(self.handler.num_project_jobs(), 5)

    def test_is_valid_job_index(self):
        self.handler.num_project_jobs = Mock(return_value=3)
        self.assertTrue(self.handler.is_valid_job_index(0))
        self.assertFalse(self.handler.is_valid_job_index(5))

    def test_project_job(self):
        self.handler.is_valid_job_index = Mock(return_value=True)
        self.holder.project_job.return_value = 'job'
        self.assertEqual(self.handler.project_job(0), 'job')

    def test_is_valid_index_in(self):
        obj = Mock()
        obj.sub_actions = [1, 2, 3]
        self.assertTrue(self.handler.is_valid_index_in(obj, 1))
        self.assertFalse(self.handler.is_valid_index_in(obj, 5))
        self.assertFalse(self.handler.is_valid_index_in(None, 0))

    def test_project_action(self):
        job = Mock()
        job.sub_actions = [Mock(), Mock()]
        self.handler.project_job = Mock(return_value=job)
        self.handler.is_valid_index_in = Mock(return_value=True)
        result = self.handler.project_action(0, 1)
        self.assertEqual(result, job.sub_actions[1])

    def test_project_subaction(self):
        action = Mock()
        action.sub_actions = [Mock(), Mock()]
        self.handler.project_action = Mock(return_value=action)
        self.handler.is_valid_index_in = Mock(return_value=True)
        result = self.handler.project_subaction(0, 1, 0)
        self.assertEqual(result, action.sub_actions[0])

    def test_project_element(self):
        self.handler.project_job = Mock(return_value='job')
        self.handler.project_action = Mock(return_value='action')
        self.handler.project_subaction = Mock(return_value='subaction')
        self.assertEqual(self.handler.project_element(0), 'job')
        self.assertEqual(self.handler.project_element(0, 1), 'action')
        self.assertEqual(self.handler.project_element(0, 1, 2), 'subaction')

    def test_project_container(self):
        self.handler.project = Mock(return_value=Mock(jobs=[1, 2]))
        self.handler.project_job = Mock(return_value=Mock(sub_actions=[3, 4]))
        self.handler.project_action = Mock(return_value=Mock(sub_actions=[5, 6]))
        self.assertEqual(self.handler.project_container(), [1, 2])
        self.assertEqual(self.handler.project_container(0), [3, 4])
        self.assertEqual(self.handler.project_container(0, 1), [5, 6])

    def test_valid_indices(self):
        job = Mock()
        job.sub_actions = [Mock()]
        job.sub_actions[0].sub_actions = [Mock()]
        self.handler.project_job = Mock(return_value=job)
        self.handler.is_valid_index_in = Mock(side_effect=[True, True, True])
        self.assertTrue(self.handler.valid_indices(0, 0, 0))

    def test_add_job_to_project(self):
        job = Mock()
        self.handler.add_job_to_project(job)
        self.holder.add_job_to_project.assert_called_with(job)

    def test_modified(self):
        self.holder.modified = True
        self.assertTrue(self.handler.modified())

    def test_set_modified(self):
        self.handler.set_modified(True)
        self.holder.set_modified.assert_called_with(True)

    def test_mark_as_not_modified(self):
        self.handler.mark_as_not_modified()
        self.holder.mark_as_not_modified.assert_called_once()

    def test_save_undo_state(self):
        pre_state = Mock()
        self.handler.save_undo_state(pre_state, 'test', 'move', (0,), (1,))
        self.holder.save_undo_state.assert_called_once()

    def test_undo_manager(self):
        self.assertEqual(self.handler.undo_manager(), self.holder.undo_manager)

    def test_reset_undo(self):
        self.handler.reset_undo()
        self.holder.reset_undo.assert_called_once()

    def test_add_undo(self):
        item = Mock()
        self.handler.add_undo(item, 'test', 'delete', (0,), (1,))
        self.holder.add_undo.assert_called_once()

    def test_pop_undo(self):
        self.holder.pop_undo.return_value = 'entry'
        self.assertEqual(self.handler.pop_undo(), 'entry')

    def test_filled_undo(self):
        self.holder.filled_undo.return_value = True
        self.assertTrue(self.handler.filled_undo())

    def test_undo(self):
        self.holder.undo.return_value = 'result'
        self.assertEqual(self.handler.undo(), 'result')

    def test_pop_redo(self):
        self.holder.pop_redo.return_value = 'entry'
        self.assertEqual(self.handler.pop_redo(), 'entry')

    def test_filled_redo(self):
        self.holder.filled_redo.return_value = True
        self.assertTrue(self.handler.filled_redo())

    def test_redo(self):
        self.holder.redo.return_value = 'result'
        self.assertEqual(self.handler.redo(), 'result')

    def test_reset_project(self):
        self.handler.reset_project()
        self.holder.reset_project.assert_called_once()

    def test_copy_buffer(self):
        self.holder.copy_buffer = 'buffer'
        self.assertEqual(self.handler.copy_buffer(), 'buffer')

    def test_set_copy_buffer(self):
        item = Mock()
        self.handler.set_copy_buffer(item)
        self.holder.set_copy_buffer.assert_called_with(item)

    def test_has_copy_buffer(self):
        self.holder.has_copy_buffer.return_value = True
        self.assertTrue(self.handler.has_copy_buffer())

    def test_current_file_path(self):
        self.holder.current_file_path = '/path'
        self.assertEqual(self.handler.current_file_path(), '/path')

    def test_current_file_directory(self):
        self.holder.current_file_directory.return_value = '/dir'
        self.assertEqual(self.handler.current_file_directory(), '/dir')

    def test_current_file_name(self):
        self.holder.current_file_name.return_value = 'file.txt'
        self.assertEqual(self.handler.current_file_name(), 'file.txt')

    def test_set_current_file_path(self):
        self.handler.set_current_file_path('/path')
        self.holder.set_current_file_path.assert_called_with('/path')


class TestProjectIOHandler(unittest.TestCase):
    def setUp(self):
        self.holder = Mock()
        self.io_handler = ProjectIOHandler(self.holder)
        self.test_project = Project()
        self.test_project.jobs = []

    def test_open_project(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_data = {'project': {'jobs': []}, 'version': 1}
            tmp.write(json.dumps(json_data))
            tmp.flush()
            with patch.object(Project, 'from_dict', return_value=self.test_project) as mock_from:
                result = self.io_handler.open_project(tmp.name)
                self.assertEqual(result, os.path.abspath(tmp.name))
                mock_from.assert_called_once()
                self.holder.set_project.assert_called_with(self.test_project)
                self.holder.set_current_file_path.assert_called_with(tmp.name)
                self.holder.mark_as_not_modified.assert_called_once()
                self.holder.reset_undo.assert_called_once()
            os.unlink(tmp.name)

    def test_open_project_invalid(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
            json_data = {'project': {'jobs': []}, 'version': 1}
            tmp.write(json.dumps(json_data))
            tmp.flush()
            with patch.object(Project, 'from_dict', return_value=None):
                with self.assertRaises(InvalidProjectError):
                    self.io_handler.open_project(tmp.name)
            os.unlink(tmp.name)

    def test_do_save(self):
        self.holder.project.return_value = self.test_project
        self.test_project.to_dict = Mock(return_value={'jobs': []})
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
            with patch('jsonpickle.encode', return_value='{"project": {}, "version": 1}'):
                self.io_handler.do_save(tmp.name)
                self.holder.mark_as_not_modified.assert_called_once()
            os.unlink(tmp.name)


if __name__ == 'main':
    unittest.main()
