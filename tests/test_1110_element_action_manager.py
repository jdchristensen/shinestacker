import unittest
from unittest.mock import Mock, patch
from shinestacker.common_project.element_action_manager import ElementActionManager
from shinestacker.common_project.selection_state import SelectionState
from shinestacker.config.constants import constants


class MockElement:
    def __init__(self, name='test', type_name=None, enabled=True):
        if type_name is None:
            type_name = constants.ACTION_TYPES[0] if constants.ACTION_TYPES else 'action1'
        self.params = {'name': name}
        self.type_name = type_name
        self.sub_actions = []
        self._enabled = enabled

    def clone(self, name_postfix=''):
        new_elem = MockElement(
            self.params.get('name', '') + name_postfix,
            self.type_name,
            self._enabled
        )
        new_elem.sub_actions = [sa.clone() for sa in self.sub_actions]
        return new_elem

    def enabled(self):
        return self._enabled

    def set_enabled(self, value):
        self._enabled = value

    def set_enabled_all(self, value):
        self._enabled = value
        for sa in self.sub_actions:
            sa.set_enabled_all(value)


class MockProject:
    def __init__(self):
        self.jobs = []


class MockProjectHolder:
    def __init__(self):
        self._project = MockProject()
        self._copy_buffer = None

    def project(self):
        return self._project

    def num_project_jobs(self):
        return len(self._project.jobs)

    def project_job(self, index):
        if 0 <= index < len(self._project.jobs):
            return self._project.jobs[index]
        return None

    def copy_buffer(self):
        return self._copy_buffer

    def set_copy_buffer(self, element):
        self._copy_buffer = element

    def has_copy_buffer(self):
        return self._copy_buffer is not None


class TestElementActionManager(unittest.TestCase):
    def setUp(self):
        self.project_holder = MockProjectHolder()
        self.selection_state = SelectionState()
        self.manager = ElementActionManager(self.project_holder, self.selection_state)
        self.manager.mark_as_modified = Mock()
        self.manager.parent = Mock(return_value=None)
        self.manager.project = lambda: self.project_holder.project()
        self.manager.project_job = lambda idx: self.project_holder.project_job(idx)
        self.manager.num_project_jobs = lambda: self.project_holder.num_project_jobs()

    def test_init(self):
        self.assertIsNotNone(self.manager.selection_state)
        self.assertEqual(self.manager.selection_state, self.selection_state)

    def test_is_job_selected(self):
        self.selection_state.set_job(0)
        self.assertTrue(self.manager.is_job_selected())
        self.selection_state.reset()
        self.assertFalse(self.manager.is_job_selected())

    def test_is_action_selected(self):
        self.selection_state.set_action(0, 1)
        self.assertTrue(self.manager.is_action_selected())
        self.selection_state.reset()
        self.assertFalse(self.manager.is_action_selected())

    def test_is_subaction_selected(self):
        self.selection_state.set_subaction(0, 1, 2)
        self.assertTrue(self.manager.is_subaction_selected())
        self.selection_state.reset()
        self.assertFalse(self.manager.is_subaction_selected())

    def test_get_selected_job_index(self):
        self.selection_state.set_job(5)
        self.assertEqual(self.manager.get_selected_job_index(), 5)

    def test_is_valid_selection(self):
        self.selection_state.set_job(0)
        self.assertTrue(self.manager.is_valid_selection())
        self.selection_state.reset()
        self.assertFalse(self.manager.is_valid_selection())

    def test_new_state_after_delete_job(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        job3 = MockElement('Job3', constants.ACTION_JOB)
        self.project_holder.project().jobs = [job1, job2, job3]
        state = SelectionState(2)
        new_state = self.manager.new_state_after_delete(state)
        self.assertEqual(new_state.job_index, 2)

    def test_new_state_after_delete_first_job(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        self.project_holder.project().jobs = [job1]
        state = SelectionState(0)
        new_state = self.manager.new_state_after_delete(state)
        self.assertEqual(new_state.job_index, 0)

    def test_new_state_after_clone_job(self):
        state = SelectionState(1)
        new_state = self.manager.new_state_after_clone(state)
        self.assertEqual(new_state.job_index, 2)

    def test_new_state_after_clone_action(self):
        state = SelectionState(1, 2)
        new_state = self.manager.new_state_after_clone(state)
        self.assertEqual(new_state.action_index, 3)

    def test_new_state_after_clone_subaction(self):
        state = SelectionState(1, 2, 3)
        new_state = self.manager.new_state_after_clone(state)
        self.assertEqual(new_state.subaction_index, 4)

    def test_get_action_with_action_selected(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0])
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_action(0, 0)
        result = self.manager.get_action(self.selection_state)
        self.assertEqual(result, action)

    def test_get_action_with_subaction_selected(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_COMBO)
        subaction = MockElement('SubAction1', constants.SUB_ACTION_TYPES[0])
        action.sub_actions.append(subaction)
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_subaction(0, 0, 0)
        result = self.manager.get_action(self.selection_state)
        self.assertEqual(result, subaction)

    def test_get_job_actions(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0])
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        result = self.manager.get_job_actions(self.selection_state)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], action)

    def test_copy_job(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        self.manager.copy_job()
        self.assertIsNotNone(self.project_holder.copy_buffer())
        self.assertEqual(self.project_holder.copy_buffer().params['name'], 'Job1')

    def test_copy_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0])
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_action(0, 0)
        self.manager.copy_action()
        self.assertIsNotNone(self.project_holder.copy_buffer())
        self.assertEqual(self.project_holder.copy_buffer().params['name'], 'Action1')

    def test_copy_subaction(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_COMBO)
        subaction = MockElement('SubAction1', constants.SUB_ACTION_TYPES[0])
        action.sub_actions.append(subaction)
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_subaction(0, 0, 0)
        self.manager.copy_subaction()
        self.assertIsNotNone(self.project_holder.copy_buffer())
        self.assertEqual(self.project_holder.copy_buffer().params['name'], 'SubAction1')

    def test_clone_job(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        success, new_state = self.manager.clone_element()
        self.assertTrue(success)
        self.assertEqual(new_state.job_index, 1)
        self.assertEqual(len(self.project_holder.project().jobs), 2)
        self.assertIn('(clone)', self.project_holder.project().jobs[1].params['name'])

    def test_clone_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0])
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_action(0, 0)
        success, new_state = self.manager.clone_element()
        self.assertTrue(success)
        self.assertEqual(new_state.action_index, 1)
        self.assertEqual(len(job.sub_actions), 2)
        self.assertIn('(clone)', job.sub_actions[1].params['name'])

    def test_op_delete_job(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        self.project_holder.project().jobs = [job1, job2]
        deleted = self.manager._op_delete_job(0)
        self.assertEqual(deleted, job1)
        self.assertEqual(len(self.project_holder.project().jobs), 1)
        self.assertEqual(self.project_holder.project().jobs[0], job2)

    def test_op_delete_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action1 = MockElement('Action1', constants.ACTION_TYPES[0])
        action2 = MockElement('Action2', constants.ACTION_TYPES[0])
        job.sub_actions = [action1, action2]
        self.project_holder.project().jobs.append(job)
        deleted = self.manager._op_delete_action(0, 0)
        self.assertEqual(deleted, action1)
        self.assertEqual(len(job.sub_actions), 1)
        self.assertEqual(job.sub_actions[0], action2)

    def test_op_delete_subaction(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_COMBO)
        sub1 = MockElement('Sub1', constants.SUB_ACTION_TYPES[0])
        sub2 = MockElement('Sub2', constants.SUB_ACTION_TYPES[0])
        action.sub_actions = [sub1, sub2]
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        deleted = self.manager._op_delete_subaction(0, 0, 0)
        self.assertEqual(deleted, sub1)
        self.assertEqual(len(action.sub_actions), 1)
        self.assertEqual(action.sub_actions[0], sub2)

    def test_shift_job_down(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        self.project_holder.project().jobs = [job1, job2]
        self.selection_state.set_job(0)
        result = self.manager._shift_job(1)
        self.assertIsNotNone(result)
        self.assertEqual(self.project_holder.project().jobs[0], job2)
        self.assertEqual(self.project_holder.project().jobs[1], job1)
        self.assertEqual(self.selection_state.job_index, 1)

    def test_shift_job_up(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        self.project_holder.project().jobs = [job1, job2]
        self.selection_state.set_job(1)
        result = self.manager._shift_job(-1)
        self.assertIsNotNone(result)
        self.assertEqual(self.project_holder.project().jobs[0], job2)
        self.assertEqual(self.project_holder.project().jobs[1], job1)
        self.assertEqual(self.selection_state.job_index, 0)

    def test_shift_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action1 = MockElement('Action1', constants.ACTION_TYPES[0])
        action2 = MockElement('Action2', constants.ACTION_TYPES[0])
        job.sub_actions = [action1, action2]
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_action(0, 0)
        result = self.manager._shift_action(1)
        self.assertIsNotNone(result)
        self.assertEqual(job.sub_actions[0], action2)
        self.assertEqual(job.sub_actions[1], action1)
        self.assertEqual(self.selection_state.action_index, 1)

    def test_set_enabled_job(self):
        job = MockElement('Job1', constants.ACTION_JOB, enabled=True)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        result = self.manager.set_enabled(False, self.selection_state)
        self.assertTrue(result)
        self.assertFalse(job.enabled())

    def test_set_enabled_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0], enabled=True)
        job.sub_actions.append(action)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_action(0, 0)
        result = self.manager.set_enabled(False, self.selection_state)
        self.assertTrue(result)
        self.assertFalse(action.enabled())

    def test_set_enabled_all(self):
        job1 = MockElement('Job1', constants.ACTION_JOB, enabled=True)
        job2 = MockElement('Job2', constants.ACTION_JOB, enabled=True)
        self.project_holder.project().jobs = [job1, job2]
        self.manager.set_enabled_all(False)
        self.assertFalse(job1.enabled())
        self.assertFalse(job2.enabled())

    @patch('shinestacker.common_project.element_action_manager.QMessageBox')
    def test_delete_element_job_with_confirm(self, mock_msgbox):
        mock_msgbox.question.return_value = mock_msgbox.Yes
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        deleted, new_state = self.manager.delete_element(confirm=True)
        self.assertIsNotNone(deleted)
        self.assertEqual(deleted.params['name'], 'Job1')
        self.assertEqual(len(self.project_holder.project().jobs), 0)

    @patch('shinestacker.common_project.element_action_manager.QMessageBox')
    def test_delete_element_cancelled(self, mock_msgbox):
        mock_msgbox.question.return_value = mock_msgbox.No
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        deleted, new_state = self.manager.delete_element(confirm=True)
        self.assertIsNone(deleted)
        self.assertEqual(len(self.project_holder.project().jobs), 1)

    def test_cut_element(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project_holder.project().jobs.append(job)
        self.selection_state.set_job(0)
        deleted, new_state = self.manager.cut_element()
        self.assertIsNotNone(deleted)
        self.assertEqual(len(self.project_holder.project().jobs), 0)
        self.assertIsNotNone(self.project_holder.copy_buffer())


if __name__ == '__main__':
    unittest.main()
