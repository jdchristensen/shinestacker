import unittest
from shinestacker.common_project.selection_state import SelectionState


class TestSelectionState(unittest.TestCase):

    def test_init_default(self):
        state = SelectionState()
        self.assertEqual(state.job_index, -1)
        self.assertEqual(state.action_index, -1)
        self.assertEqual(state.subaction_index, -1)
        self.assertEqual(state.type(), '')

    def test_init_with_job(self):
        state = SelectionState(job_index=5)
        self.assertEqual(state.job_index, 5)
        self.assertEqual(state.type(), 'job')

    def test_init_with_action(self):
        state = SelectionState(job_index=2, action_index=3)
        self.assertEqual(state.job_index, 2)
        self.assertEqual(state.action_index, 3)
        self.assertEqual(state.type(), 'action')

    def test_init_with_subaction(self):
        state = SelectionState(job_index=1, action_index=2, subaction_index=3)
        self.assertEqual(state.job_index, 1)
        self.assertEqual(state.action_index, 2)
        self.assertEqual(state.subaction_index, 3)
        self.assertEqual(state.type(), 'subaction')

    def test_reset(self):
        state = SelectionState(1, 2, 3)
        state.reset()
        self.assertEqual(state.job_index, -1)
        self.assertEqual(state.action_index, -1)
        self.assertEqual(state.subaction_index, -1)
        self.assertEqual(state.type(), '')

    def test_is_job_selected(self):
        state = SelectionState(job_index=0)
        self.assertTrue(state.is_job_selected())
        state.set_indices(0, 1)
        self.assertFalse(state.is_job_selected())

    def test_is_action_selected(self):
        state = SelectionState(job_index=0, action_index=1)
        self.assertTrue(state.is_action_selected())
        state.set_indices(0)
        self.assertFalse(state.is_action_selected())

    def test_is_subaction_selected(self):
        state = SelectionState(job_index=0, action_index=1, subaction_index=2)
        self.assertTrue(state.is_subaction_selected())
        state.set_indices(0, 1)
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
        self.assertEqual(state2.type(), 'subaction')

    def test_get_indices(self):
        state = SelectionState(7, 8, 9)
        self.assertEqual(state.get_indices(), (7, 8, 9))

    def test_are_indices_valid(self):
        state = SelectionState(job_index=0)
        self.assertTrue(state.is_valid())
        state.reset()
        self.assertFalse(state.is_valid())

    def test_copy(self):
        state1 = SelectionState(1, 2, 3)
        state2 = state1.copy()
        self.assertEqual(state2.job_index, 1)
        self.assertEqual(state2.action_index, 2)
        self.assertEqual(state2.subaction_index, 3)
        self.assertEqual(state2.type(), 'subaction')
        state1.reset()
        self.assertEqual(state2.job_index, 1)

    def test_type_method(self):
        state = SelectionState()
        self.assertEqual(state.type(), '')
        state.set_indices(0)
        self.assertEqual(state.type(), 'job')
        state.set_indices(0, 1)
        self.assertEqual(state.type(), 'action')
        state.set_indices(0, 1, 2)
        self.assertEqual(state.type(), 'subaction')
        state.reset()
        self.assertEqual(state.type(), '')

    def test_set_indices_method(self):
        state = SelectionState()
        state.set_indices(1, 2, 3)
        self.assertEqual(state.job_index, 1)
        self.assertEqual(state.action_index, 2)
        self.assertEqual(state.subaction_index, 3)


if __name__ == '__main__':
    unittest.main()
