import unittest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from shinestacker.core.exceptions import InvalidProjectError
from shinestacker.gui.project_model import Project
from shinestacker.common_project.project_handler import ProjectHandler, ProjectHolder


class TestProjectHandler(unittest.TestCase):
    def setUp(self):
        self.holder = ProjectHolder()
        self.handler = ProjectHandler(self.holder)
        self.test_project = Project()
        self.test_project.jobs = [Mock(), Mock()]
        self.holder.project = self.test_project

    def test_project(self):
        self.assertEqual(self.handler.project(), self.test_project)

    def test_set_project(self):
        new_project = Project()
        new_project.jobs = [Mock()]
        self.handler.set_project(new_project)
        self.assertEqual(self.holder.project, new_project)

    def test_project_jobs(self):
        self.assertEqual(self.handler.project_jobs(), self.test_project.jobs)

    def test_num_project_jobs(self):
        self.assertEqual(self.handler.num_project_jobs(), 2)

    def test_is_valid_job_index(self):
        self.assertTrue(self.handler.is_valid_job_index(0))
        self.assertTrue(self.handler.is_valid_job_index(1))
        self.assertFalse(self.handler.is_valid_job_index(2))
        self.assertFalse(self.handler.is_valid_job_index(-1))

    def test_project_job(self):
        self.assertEqual(self.handler.project_job(0), self.test_project.jobs[0])
        self.assertEqual(self.handler.project_job(1), self.test_project.jobs[1])
        self.assertIsNone(self.handler.project_job(2))
        self.assertIsNone(self.handler.project_job(-1))

    def test_is_valid_index_in(self):
        obj_with_actions = Mock()
        obj_with_actions.sub_actions = [1, 2, 3]
        obj_no_actions = Mock()
        obj_no_actions.sub_actions = []
        self.assertTrue(self.handler.is_valid_index_in(obj_with_actions, 0))
        self.assertTrue(self.handler.is_valid_index_in(obj_with_actions, 2))
        self.assertFalse(self.handler.is_valid_index_in(obj_with_actions, 3))
        self.assertFalse(self.handler.is_valid_index_in(obj_with_actions, -1))
        self.assertFalse(self.handler.is_valid_index_in(obj_no_actions, 0))
        self.assertFalse(self.handler.is_valid_index_in(None, 0))

    def test_project_action(self):
        job = Mock()
        action1 = Mock()
        action2 = Mock()
        job.sub_actions = [action1, action2]
        self.test_project.jobs[0] = job
        self.assertEqual(self.handler.project_action(0, 0), action1)
        self.assertEqual(self.handler.project_action(0, 1), action2)
        self.assertIsNone(self.handler.project_action(0, 2))
        self.assertIsNone(self.handler.project_action(2, 0))
        self.assertIsNone(self.handler.project_action(-1, 0))

    def test_project_subaction(self):
        job = Mock()
        action = Mock()
        subaction1 = Mock()
        subaction2 = Mock()
        action.sub_actions = [subaction1, subaction2]
        job.sub_actions = [action]
        self.test_project.jobs[0] = job
        self.assertEqual(self.handler.project_subaction(0, 0, 0), subaction1)
        self.assertEqual(self.handler.project_subaction(0, 0, 1), subaction2)
        self.assertIsNone(self.handler.project_subaction(0, 0, 2))
        self.assertIsNone(self.handler.project_subaction(0, 1, 0))
        self.assertIsNone(self.handler.project_subaction(2, 0, 0))

    def test_project_element(self):
        job = Mock()
        action = Mock()
        subaction = Mock()
        job.sub_actions = [action]
        action.sub_actions = [subaction]
        self.test_project.jobs[0] = job
        self.assertEqual(self.handler.project_element(0), job)
        self.assertEqual(self.handler.project_element(0, 0), action)
        self.assertEqual(self.handler.project_element(0, 0, 0), subaction)
        self.assertIsNone(self.handler.project_element(-1))
        self.assertIsNone(self.handler.project_element(0, 5))

    def test_project_container(self):
        job = Mock()
        action = Mock()
        job.sub_actions = [action]
        action.sub_actions = [Mock(), Mock()]
        self.test_project.jobs = [job]
        self.assertEqual(self.handler.project_container(), [job])
        self.assertEqual(self.handler.project_container(0), [action])
        self.assertEqual(len(self.handler.project_container(0, 0)), 2)

    def test_valid_indices(self):
        job = Mock()
        action = Mock()
        job.sub_actions = [action]
        action.sub_actions = [Mock()]
        self.test_project.jobs = [job]
        
        self.assertTrue(self.handler.valid_indices(0))
        self.assertTrue(self.handler.valid_indices(0, 0))
        self.assertTrue(self.handler.valid_indices(0, 0, 0))
        self.assertFalse(self.handler.valid_indices(1))
        self.assertFalse(self.handler.valid_indices(0, 1))
        self.assertFalse(self.handler.valid_indices(0, 0, 1))

    def test_add_job_to_project(self):
        new_job = Mock()
        initial_count = len(self.test_project.jobs)
        self.handler.add_job_to_project(new_job)
        self.assertEqual(len(self.test_project.jobs), initial_count + 1)
        self.assertEqual(self.test_project.jobs[-1], new_job)

    def test_reset_project(self):
        self.holder.reset_project = Mock()
        self.handler.reset_project()
        self.holder.reset_project.assert_called_once()

    def test_copy_buffer(self):
        self.assertIsNone(self.handler.copy_buffer())
        buffer_item = Mock()
        self.handler.project_holder._copy_buffer = buffer_item
        self.assertEqual(self.handler.copy_buffer(), buffer_item)

    def test_set_copy_buffer(self):
        item = Mock()
        cloned_item = Mock()
        item.clone.return_value = cloned_item
        self.handler.set_copy_buffer(item)
        self.assertEqual(self.handler.project_holder._copy_buffer, cloned_item)
        item.clone.assert_called_once()

    def test_has_copy_buffer(self):
        self.assertFalse(self.handler.has_copy_buffer())
        self.handler.project_holder._copy_buffer = Mock()
        self.assertTrue(self.handler.has_copy_buffer())


if __name__ == '__main__':
    unittest.main()
