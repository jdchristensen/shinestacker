import sys
from shinestacker.common_project.selection_state import SelectionState


class TestSelectionState:
    def test_default_initialization(self):
        state = SelectionState()
        assert state.job_index == -1
        assert state.action_index == -1
        assert state.subaction_index == -1
        assert state.widget_type is None
        assert not state.is_valid()
        assert not state.is_job_selected()
        assert not state.is_action_selected()
        assert not state.is_subaction_selected()

    def test_initialization_with_indices(self):
        state = SelectionState(job_index=0, action_index=1, subaction_index=2)
        assert state.job_index == 0
        assert state.action_index == 1
        assert state.subaction_index == 2
        assert state.widget_type == 'subaction'
        assert state.is_valid()
        assert state.is_subaction_selected()

    def test_set_indices(self):
        state = SelectionState()
        state.set_indices(2, 3, 4)
        assert state.job_index == 2
        assert state.action_index == 3
        assert state.subaction_index == 4
        assert state.widget_type == 'subaction'

    def test_reset(self):
        state = SelectionState(1, 2, 3)
        state.reset()
        assert state.job_index == -1
        assert state.action_index == -1
        assert state.subaction_index == -1
        assert state.widget_type is None
        assert not state.is_valid()

    def test_set_job(self):
        state = SelectionState()
        state.set_job(5)
        assert state.job_index == 5
        assert state.action_index == -1
        assert state.subaction_index == -1
        assert state.widget_type == 'job'
        assert state.is_job_selected()
        assert not state.is_action_selected()
        assert not state.is_subaction_selected()

    def test_set_action(self):
        state = SelectionState()
        state.set_action(2, 3)
        assert state.job_index == 2
        assert state.action_index == 3
        assert state.subaction_index == -1
        assert state.widget_type == 'action'
        assert state.is_action_selected()
        assert not state.is_job_selected()
        assert not state.is_subaction_selected()

    def test_set_subaction(self):
        state = SelectionState()
        state.set_subaction(1, 2, 3)
        assert state.job_index == 1
        assert state.action_index == 2
        assert state.subaction_index == 3
        assert state.widget_type == 'subaction'
        assert state.is_subaction_selected()
        assert not state.is_job_selected()
        assert not state.is_action_selected()

    def test_is_job_selected_positive(self):
        state = SelectionState()
        state.set_job(0)
        assert state.is_job_selected()

    def test_is_job_selected_negative(self):
        state = SelectionState(job_index=-1, action_index=-1, subaction_index=-1)
        state.widget_type = 'job'
        assert not state.is_job_selected()

    def test_is_action_selected_positive(self):
        state = SelectionState()
        state.set_action(0, 1)
        assert state.is_action_selected()

    def test_is_action_selected_negative(self):
        state = SelectionState(job_index=-1, action_index=0, subaction_index=-1)
        state.widget_type = 'action'
        assert not state.is_action_selected()

    def test_is_subaction_selected_positive(self):
        state = SelectionState()
        state.set_subaction(0, 1, 2)
        assert state.is_subaction_selected()

    def test_is_subaction_selected_negative(self):
        state = SelectionState(job_index=0, action_index=-1, subaction_index=0)
        state.widget_type = 'subaction'
        assert not state.is_subaction_selected()

    def test_is_valid_for_different_types(self):
        job_state = SelectionState(0, -1, -1)
        assert job_state.is_valid()
        action_state = SelectionState(0, 1, -1)
        assert action_state.is_valid()
        subaction_state = SelectionState(0, 1, 2)
        assert subaction_state.is_valid()
        invalid_state = SelectionState(-1, -1, -1)
        assert not invalid_state.is_valid()

    def test_to_tuple(self):
        state = SelectionState(1, 2, 3)
        assert state.to_tuple() == (1, 2, 3)

    def test_from_tuple(self):
        state = SelectionState()
        state.from_tuple((4, 5, 6))
        assert state.job_index == 4
        assert state.action_index == 5
        assert state.subaction_index == 6

    def test_copy_from(self):
        source = SelectionState(2, 3, 4)
        target = SelectionState()
        target.copy_from(source)
        assert target.job_index == 2
        assert target.action_index == 3
        assert target.subaction_index == 4
        assert target.widget_type == 'subaction'

    def test_get_indices(self):
        state = SelectionState(3, 4, 5)
        assert state.get_indices() == (3, 4, 5)

    def test_is_valid(self):
        state = SelectionState(0, -1, -1)
        assert state.is_valid()
        state.job_index = -1
        assert not state.is_valid()

    def test_are_action_indices_valid(self):
        state = SelectionState(0, 1, -1)
        assert state.are_action_indices_valid()
        state.action_index = -1
        assert not state.are_action_indices_valid()
        state.job_index = -1
        state.action_index = 1
        assert not state.are_action_indices_valid()

    def test_are_subaction_indices_valid(self):
        state = SelectionState(0, 1, 2)
        assert state.are_subaction_indices_valid()
        state.subaction_index = -1
        assert not state.are_subaction_indices_valid()
        state.subaction_index = 2
        state.action_index = -1
        assert not state.are_subaction_indices_valid()
        state.action_index = 1
        state.job_index = -1
        assert not state.are_subaction_indices_valid()

    def test_set_job_indices(self):
        state = SelectionState()
        state.set_job_indices(7)
        assert state.job_index == 7
        assert state.action_index == -1
        assert state.subaction_index == -1
        assert state.widget_type == 'job'

    def test_set_action_indices(self):
        state = SelectionState()
        state.set_action_indices(3, 4)
        assert state.job_index == 3
        assert state.action_index == 4
        assert state.subaction_index == -1
        assert state.widget_type == 'action'

    def test_set_subaction_indices(self):
        state = SelectionState()
        state.set_subaction_indices(5, 6, 7)
        assert state.job_index == 5
        assert state.action_index == 6
        assert state.subaction_index == 7
        assert state.widget_type == 'subaction'

    def test_equals(self):
        state = SelectionState(1, 2, 3)
        assert state.equals(1, 2, 3)
        assert not state.equals(1, 2, 4)
        assert not state.equals(1, 3, 3)
        assert not state.equals(2, 2, 3)

    def test_is_within_bounds_job(self):
        state = SelectionState(2, -1, -1)
        state.widget_type = 'job'
        assert state.is_within_bounds(total_jobs=5)
        assert not state.is_within_bounds(total_jobs=2)

    def test_is_within_bounds_action(self):
        state = SelectionState(1, 3, -1)
        state.widget_type = 'action'
        assert state.is_within_bounds(total_jobs=5, job_actions_count=4)
        assert not state.is_within_bounds(total_jobs=5, job_actions_count=3)
        assert not state.is_within_bounds(total_jobs=1, job_actions_count=4)

    def test_is_within_bounds_subaction(self):
        state = SelectionState(0, 1, 2)
        state.widget_type = 'subaction'
        assert state.is_within_bounds(
            total_jobs=3,
            job_actions_count=2,
            action_subactions_count=3
        )
        assert not state.is_within_bounds(
            total_jobs=3,
            job_actions_count=1,
            action_subactions_count=3
        )
        assert not state.is_within_bounds(
            total_jobs=3,
            job_actions_count=2,
            action_subactions_count=2
        )

    def test_copy(self):
        original = SelectionState(4, 5, 6)
        copied = original.copy()
        assert copied.job_index == original.job_index
        assert copied.action_index == original.action_index
        assert copied.subaction_index == original.subaction_index
        assert copied.widget_type == original.widget_type
        original.set_job(10)
        assert copied.job_index == 4
        assert original.job_index == 10

    def test_edge_cases(self):
        state = SelectionState(-1, -1, -1)
        state.widget_type = 'job'
        assert not state.is_job_selected()
        state = SelectionState(1000, 2000, 3000)
        assert state.widget_type == 'subaction'
        assert state.is_subaction_selected()
        state = SelectionState(0, 0, 0)
        assert state.widget_type == 'subaction'
        assert state.is_subaction_selected()

    def test_widget_type_determination_on_construction(self):
        state1 = SelectionState(0, -1, -1)
        assert state1.widget_type == 'job'
        state2 = SelectionState(0, 1, -1)
        assert state2.widget_type == 'action'
        state3 = SelectionState(0, 1, 2)
        assert state3.widget_type == 'subaction'
        state4 = SelectionState(-1, -1, -1)
        assert state4.widget_type is None

    def test_inconsistent_state_handling(self):
        state = SelectionState(0, 1, 2)
        state.widget_type = 'job'
        assert state.is_job_selected()
        assert not state.is_subaction_selected()
        assert state.is_valid()


if __name__ == "__main__":
    test_class = TestSelectionState()
    test_count = 0
    failed = []
    for method_name in dir(test_class):
        if method_name.startswith('test_'):
            test_count += 1
            method = getattr(test_class, method_name)
            try:
                method()
                print(f"✓ {method_name}")
            except AssertionError as e:
                failed.append((method_name, str(e)))
                print(f"✗ {method_name}: {e}")
            except Exception as e:
                failed.append((method_name, f"Unexpected error: {e}"))
                print(f"✗ {method_name}: Unexpected error: {e}")
    print(f"\nTotal tests: {test_count}")
    print(f"Passed: {test_count - len(failed)}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("\nFailed tests:")
        for name, error in failed:
            print(f"  {name}: {error}")
        sys.exit(1)
