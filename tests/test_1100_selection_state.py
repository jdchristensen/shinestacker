import unittest
from shinestacker.common_project.selection_state import SelectionState


class TestSelectionState(unittest.TestCase):

    def test_init_default(self):
        state = SelectionState()
        self.assertEqual(state.job_index, -1)
        self.assertEqual(state.action_index, -1)
        self.assertEqual(state.subaction_index, -1)
        self.assertIsNone(state.widget_type)

    def test_init_with_job(self):
        state = SelectionState(job_index=5)
        self.assertEqual(state.job_index, 5)
        self.assertEqual(state.widget_type, 'job')

    def test_init_with_action(self):
        state = SelectionState(job_index=2, action_index=3)
        self.assertEqual(state.job_index, 2)
        self.assertEqual(state.action_index, 3)
        self.assertEqual(state.widget_type, 'action')

    def test_init_with_subaction(self):
        state = SelectionState(job_index=1, action_index=2, subaction_index=3)
        self.assertEqual(state.job_index, 1)
        self.assertEqual(state.action_index, 2)
        self.assertEqual(state.subaction_index, 3)
        self.assertEqual(state.widget_type, 'subaction')

    def test_reset(self):
        state = SelectionState(1, 2, 3)
        state.reset()
        self.assertEqual(state.job_index, -1)
        self.assertEqual(state.action_index, -1)
        self.assertEqual(state.subaction_index, -1)
        self.assertIsNone(state.widget_type)

    def test_set_job(self):
        state = SelectionState()
        state.set_job(5)
        self.assertEqual(state.job_index, 5)
        self.assertEqual(state.action_index, -1)
        self.assertEqual(state.subaction_index, -1)
        self.assertEqual(state.widget_type, 'job')

    def test_set_action(self):
        state = SelectionState()
        state.set_action(2, 4)
        self.assertEqual(state.job_index, 2)
        self.assertEqual(state.action_index, 4)
        self.assertEqual(state.subaction_index, -1)
        self.assertEqual(state.widget_type, 'action')

    def test_set_subaction(self):
        state = SelectionState()
        state.set_subaction(1, 2, 3)
        self.assertEqual(state.job_index, 1)
        self.assertEqual(state.action_index, 2)
        self.assertEqual(state.subaction_index, 3)
        self.assertEqual(state.widget_type, 'subaction')

    def test_is_job_selected(self):
        state = SelectionState(job_index=0)
        self.assertTrue(state.is_job_selected())
        state.set_action(0, 1)
        self.assertFalse(state.is_job_selected())

    def test_is_action_selected(self):
        state = SelectionState(job_index=0, action_index=1)
        self.assertTrue(state.is_action_selected())
        state.set_job(0)
        self.assertFalse(state.is_action_selected())

    def test_is_subaction_selected(self):
        state = SelectionState(job_index=0, action_index=1, subaction_index=2)
        self.assertTrue(state.is_subaction_selected())
        state.set_action(0, 1)
        self.assertFalse(state.is_subaction_selected())

    def test_is_valid(self):
        state = SelectionState(job_index=0)
        self.assertTrue(state.is_valid())
        state.reset()
        self.assertFalse(state.is_valid())

    def test_to_tuple(self):
        state = SelectionState(1, 2, 3)
        self.assertEqual(state.to_tuple(), (1, 2, 3))

    def test_from_tuple(self):
        state = SelectionState()
        state.from_tuple((5, 6, 7))
        self.assertEqual(state.job_index, 5)
        self.assertEqual(state.action_index, 6)
        self.assertEqual(state.subaction_index, 7)

    def test_copy_from(self):
        state1 = SelectionState(1, 2, 3)
        state2 = SelectionState()
        state2.copy_from(state1)
        self.assertEqual(state2.job_index, 1)
        self.assertEqual(state2.action_index, 2)
        self.assertEqual(state2.subaction_index, 3)
        self.assertEqual(state2.widget_type, 'subaction')

    def test_get_indices(self):
        state = SelectionState(7, 8, 9)
        self.assertEqual(state.get_indices(), (7, 8, 9))

    def test_are_indices_valid(self):
        state = SelectionState(job_index=0)
        self.assertTrue(state.are_indices_valid())
        state.reset()
        self.assertFalse(state.are_indices_valid())

    def test_are_action_indices_valid(self):
        state = SelectionState(job_index=0, action_index=1)
        self.assertTrue(state.are_action_indices_valid())
        state.set_job(0)
        self.assertFalse(state.are_action_indices_valid())

    def test_are_subaction_indices_valid(self):
        state = SelectionState(job_index=0, action_index=1, subaction_index=2)
        self.assertTrue(state.are_subaction_indices_valid())
        state.set_action(0, 1)
        self.assertFalse(state.are_subaction_indices_valid())

    def test_equals(self):
        state = SelectionState(1, 2, 3)
        self.assertTrue(state.equals(1, 2, 3))
        self.assertFalse(state.equals(1, 2, 4))

    def test_is_within_bounds_job(self):
        state = SelectionState(job_index=2)
        self.assertTrue(state.is_within_bounds(5))
        self.assertFalse(state.is_within_bounds(2))

    def test_is_within_bounds_action(self):
        state = SelectionState(job_index=1, action_index=2)
        self.assertTrue(state.is_within_bounds(5, job_actions_count=3))
        self.assertFalse(state.is_within_bounds(5, job_actions_count=2))

    def test_is_within_bounds_subaction(self):
        state = SelectionState(job_index=1, action_index=2, subaction_index=3)
        self.assertTrue(state.is_within_bounds(5, 5, action_subactions_count=4))
        self.assertFalse(state.is_within_bounds(5, 5, action_subactions_count=3))

    def test_copy(self):
        state1 = SelectionState(1, 2, 3)
        state2 = state1.copy()
        self.assertEqual(state2.job_index, 1)
        self.assertEqual(state2.action_index, 2)
        self.assertEqual(state2.subaction_index, 3)
        self.assertEqual(state2.widget_type, 'subaction')
        state1.reset()
        self.assertEqual(state2.job_index, 1)


if __name__ == '__main__':
    unittest.main()
