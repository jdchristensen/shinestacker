import unittest
from unittest.mock import Mock, patch
from shinestacker.project.element_action_manager import ElementActionManager
from shinestacker.common_project.selection_state import SelectionState
from shinestacker.project.project_undo_manager import ProjectUndoManager
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

    def clone(self):
        new_project = MockProject()
        new_project.jobs = [job.clone() for job in self.jobs]
        return new_project

    def copy_from(self, other):
        self.jobs = [job.clone() for job in other.jobs]


class TestElementActionManager(unittest.TestCase):
    def setUp(self):
        self.project = MockProject()
        self.selection_state = SelectionState()
        self.undo_manager = ProjectUndoManager()
        self.manager = ElementActionManager(
            self.project, self.undo_manager, self.selection_state)
        self.manager.save_undo_state = Mock()
        self.manager.parent = Mock(return_value=None)
        self.manager.project = Mock(return_value=self.project)
        self.manager.set_project = Mock()

    def _mock_project_element(self, job_idx, act_idx=-1, sub_idx=-1):
        if job_idx < 0:
            return None
        if act_idx < 0:
            return self.manager.project_job(job_idx)
        job = self.manager.project_job(job_idx)
        if not job or act_idx >= len(job.sub_actions):
            return None
        if sub_idx < 0:
            return job.sub_actions[act_idx]
        action = job.sub_actions[act_idx]
        if not hasattr(action, 'sub_actions') or sub_idx >= len(action.sub_actions):
            return None
        return action.sub_actions[sub_idx]

    def _mock_project_container(self, job_idx=-1, act_idx=-1):
        # Use the actual ProjectHandler methods that are inherited
        if job_idx < 0:
            return self.manager.project().jobs
        job = self.manager.project_job(job_idx)
        if not job:
            return None
        if act_idx < 0:
            return job.sub_actions
        if act_idx >= len(job.sub_actions):
            return None
        action = job.sub_actions[act_idx]
        if not hasattr(action, 'sub_actions'):
            return None
        return action.sub_actions

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
        self.assertEqual(self.selection_state.job_index, 5)

    def test_new_state_after_delete_job(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        job3 = MockElement('Job3', constants.ACTION_JOB)
        self.project.jobs = [job1, job2, job3]
        state = SelectionState(2)
        new_state = self.manager.new_state_after_delete(state)
        self.assertEqual(new_state.job_index, 2)

    def test_new_state_after_delete_first_job(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        self.project.jobs = [job1]
        state = SelectionState(0)
        new_state = self.manager.new_state_after_delete(state)
        self.assertEqual(new_state.job_index, 0)

    def test_copy_element(self):
        self.project.jobs = []
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project.jobs.append(job)
        self.selection_state.set_job(0)
        self.manager.copy_element()
        self.assertIsNotNone(self.manager.copy_buffer())
        self.assertEqual(self.manager.copy_buffer().params['name'], 'Job1')
        self.project.jobs = []
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0])
        job.sub_actions.append(action)
        self.project.jobs.append(job)
        self.selection_state.set_action(0, 0)
        self.manager.copy_element()
        self.assertEqual(self.manager.copy_buffer().params['name'], 'Action1')
        self.project.jobs = []
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_COMBO)
        subaction = MockElement('SubAction1', constants.SUB_ACTION_TYPES[0])
        action.sub_actions.append(subaction)
        job.sub_actions.append(action)
        self.project.jobs.append(job)
        self.selection_state.set_subaction(0, 0, 0)
        self.manager.copy_element()
        self.assertEqual(self.manager.copy_buffer().params['name'], 'SubAction1')

    def test_clone_job(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project.jobs.append(job)
        self.selection_state.set_job(0)
        success = self.manager.clone_element()
        self.assertTrue(success)
        self.assertEqual(len(self.project.jobs), 2)
        self.assertIn('(clone)', self.project.jobs[1].params['name'])

    def test_clone_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0])
        job.sub_actions.append(action)
        self.project.jobs.append(job)
        self.selection_state.set_action(0, 0)
        success = self.manager.clone_element()
        self.assertTrue(success)
        self.assertEqual(len(job.sub_actions), 2)
        self.assertIn('(clone)', job.sub_actions[1].params['name'])

    def test_delete_job(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        self.project.jobs = [job1, job2]
        self.selection_state.set_job(0)
        with patch.object(self.manager, 'confirm_delete_message', return_value=True):
            success = self.manager.delete_element()
        self.assertEqual(success, True)
        self.assertEqual(len(self.project.jobs), 1)
        self.assertEqual(self.project.jobs[0], job2)

    def test_delete_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action1 = MockElement('Action1', constants.ACTION_TYPES[0])
        action2 = MockElement('Action2', constants.ACTION_TYPES[0])
        job.sub_actions = [action1, action2]
        self.project.jobs.append(job)
        self.selection_state.set_action(0, 0)
        with patch.object(self.manager, 'confirm_delete_message', return_value=True):
            success = self.manager.delete_element()
        self.assertEqual(success, True)
        self.assertEqual(len(job.sub_actions), 1)
        self.assertEqual(job.sub_actions[0], action2)

    def test_delete_subaction(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_COMBO)
        sub1 = MockElement('Sub1', constants.SUB_ACTION_TYPES[0])
        sub2 = MockElement('Sub2', constants.SUB_ACTION_TYPES[0])
        action.sub_actions = [sub1, sub2]
        job.sub_actions.append(action)
        self.project.jobs.append(job)
        self.selection_state.set_subaction(0, 0, 0)
        with patch.object(self.manager, 'confirm_delete_message', return_value=True):
            success = self.manager.delete_element()
        self.assertEqual(success, True)
        self.assertEqual(len(action.sub_actions), 1)
        self.assertEqual(action.sub_actions[0], sub2)

    def test_shift_element_job_down(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        self.project.jobs = [job1, job2]
        self.selection_state.set_job(0)
        result = self.manager.shift_element(1, "Down")
        self.assertTrue(result)
        self.assertEqual(self.project.jobs[0], job2)
        self.assertEqual(self.project.jobs[1], job1)
        self.assertEqual(self.selection_state.job_index, 1)

    def test_shift_element_job_up(self):
        job1 = MockElement('Job1', constants.ACTION_JOB)
        job2 = MockElement('Job2', constants.ACTION_JOB)
        self.project.jobs = [job1, job2]
        self.selection_state.set_job(1)
        result = self.manager.shift_element(-1, "Up")
        self.assertTrue(result)
        self.assertEqual(self.project.jobs[0], job2)
        self.assertEqual(self.project.jobs[1], job1)
        self.assertEqual(self.selection_state.job_index, 0)

    def test_shift_element_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action1 = MockElement('Action1', constants.ACTION_TYPES[0])
        action2 = MockElement('Action2', constants.ACTION_TYPES[0])
        job.sub_actions = [action1, action2]
        self.project.jobs.append(job)
        self.selection_state.set_action(0, 0)
        result = self.manager.shift_element(1, "Down")
        self.assertTrue(result)
        self.assertEqual(job.sub_actions[0], action2)
        self.assertEqual(job.sub_actions[1], action1)
        self.assertEqual(self.selection_state.action_index, 1)

    def test_set_enabled_job(self):
        job = MockElement('Job1', constants.ACTION_JOB, enabled=True)
        self.project.jobs.append(job)
        self.selection_state.set_job(0)
        result = self.manager.set_enabled(self.selection_state, False)
        self.assertTrue(result)
        self.assertFalse(job.enabled())

    def test_set_enabled_action(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        action = MockElement('Action1', constants.ACTION_TYPES[0], enabled=True)
        job.sub_actions.append(action)
        self.project.jobs.append(job)
        self.selection_state.set_action(0, 0)
        result = self.manager.set_enabled(self.selection_state, False)
        self.assertTrue(result)
        self.assertFalse(action.enabled())

    def test_set_enabled_all(self):
        job1 = MockElement('Job1', constants.ACTION_JOB, enabled=True)
        job2 = MockElement('Job2', constants.ACTION_JOB, enabled=True)
        self.project.jobs = [job1, job2]
        self.manager.set_enabled_all(False)
        self.assertFalse(job1.enabled())
        self.assertFalse(job2.enabled())

    @patch('shinestacker.project.element_action_manager.QMessageBox')
    def test_delete_element_job_with_confirm(self, mock_msgbox):
        mock_msgbox.question.return_value = mock_msgbox.Yes
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project.jobs.append(job)
        self.selection_state.set_job(0)
        success = self.manager.delete_element(confirm=True)
        self.assertEqual(success, True)
        self.assertEqual(len(self.project.jobs), 0)

    @patch('shinestacker.project.element_action_manager.QMessageBox')
    def test_delete_element_cancelled(self, mock_msgbox):
        mock_msgbox.question.return_value = mock_msgbox.No
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project.jobs.append(job)
        self.selection_state.set_job(0)
        success = self.manager.delete_element(confirm=True)
        self.assertEqual(success, False)
        self.assertEqual(len(self.project.jobs), 1)

    def test_cut_element(self):
        job = MockElement('Job1', constants.ACTION_JOB)
        self.project.jobs.append(job)
        self.selection_state.set_job(0)
        deleted = self.manager.cut_element()
        self.assertIsNotNone(deleted)
        self.assertEqual(len(self.project.jobs), 0)
        self.assertIsNotNone(self.manager.copy_buffer())


if __name__ == '__main__':
    unittest.main()
