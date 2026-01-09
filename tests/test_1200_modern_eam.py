from unittest.mock import Mock, patch, MagicMock
from shinestacker.modern_project.modern_element_action_manager import ModernElementActionManager
from shinestacker.common_project.selection_state import SelectionState


class TestModernElementActionManagerMinimal:

    def test_constructor_doesnt_crash(self):
        with patch.object(ModernElementActionManager, '__init__', return_value=None):
            manager = ModernElementActionManager(
                Mock(),
                SelectionState()
            )
            assert manager is not None

    def test_delete_without_confirmation_doesnt_crash(self):
        with patch.object(ModernElementActionManager, 'num_project_jobs', return_value=0):
            manager = ModernElementActionManager(
                Mock(),
                SelectionState(-1, -1, -1)
            )
            manager.refresh_ui = Mock()
            manager.remove_widget = Mock()
            manager.update_selection = Mock()
            manager.ensure_selected_visible = Mock()
            manager.move_widgets = Mock()
            manager.element_ops = Mock()
            result = manager.delete_element(confirm=False)
            assert result == (None, None, None)

    def test_new_indices_after_delete_smoke_test(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = None
        manager.element_ops = Mock()
        manager.num_project_jobs = Mock(return_value=3)
        mock_job = Mock()
        mock_action = Mock()
        mock_action.sub_actions = []
        mock_job.sub_actions = [mock_action]
        manager.project_job = Mock(return_value=mock_job)
        test_cases = [
            (0, -1, -1),
            (1, -1, -1),
            (2, -1, -1),
            (0, 0, -1),
            (0, 0, 0),
        ]
        for job_idx, act_idx, sub_idx in test_cases:
            state = SelectionState(job_idx, act_idx, sub_idx)
            result = manager.new_indices_after_delete(state)
            assert len(result) == 3
            assert all(isinstance(x, int) for x in result)

    @patch('PySide6.QtWidgets.QMessageBox.question')
    def test_delete_with_confirmation_mocked(self, mock_messagebox):
        mock_messagebox.return_value = Mock()
        with patch.object(ModernElementActionManager, 'num_project_jobs', return_value=1):
            manager = ModernElementActionManager(
                Mock(),
                SelectionState(0, -1, -1)
            )
            manager.refresh_ui = Mock()
            manager.remove_widget = Mock()
            manager.update_selection = Mock()
            manager.ensure_selected_visible = Mock()
            manager.move_widgets = Mock()
            manager.element_ops = Mock()
            mock_project = Mock()
            mock_job = Mock()
            mock_job.params = {'name': 'Test Job'}
            mock_job.sub_actions = []
            mock_project.jobs = [mock_job]
            manager.project = Mock(return_value=mock_project)
            with patch.object(manager, 'confirm_delete_message', return_value=True):
                with patch.object(manager, 'mark_as_modified'):
                    with patch.object(manager, 'new_indices_after_delete',
                                      return_value=(-1, -1, -1)):
                        result = manager.delete_element(confirm=True)
                        assert result is not None
                        assert len(result) == 3

    def test_new_indices_after_clone(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        test_cases = [
            (0, 0, 0, (0, 0, 1)),
            (1, 2, 3, (1, 2, 4)),
            (0, 1, -1, (0, 2, -1)),
            (2, -1, -1, (3, -1, -1)),
        ]
        for job_idx, act_idx, sub_idx, expected in test_cases:
            state = SelectionState(job_idx, act_idx, sub_idx)
            result = manager.new_indices_after_clone(state)
            assert result == expected

    def test_new_indices_after_insert(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.num_project_jobs = Mock(return_value=5)
        mock_job = Mock()
        mock_action = Mock()
        mock_action.sub_actions = [Mock(), Mock(), Mock()]
        mock_job.sub_actions = [mock_action, Mock(), Mock()]
        manager.project_job = Mock(return_value=mock_job)
        test_cases = [
            (0, 0, 0, 1, (0, 0, 1)),
            (0, 0, 0, -1, (0, 0, 0)),
            (0, 0, -1, 1, (0, 1, -1)),
            (0, 0, -1, -1, (0, 0, -1)),
            (0, -1, -1, 1, (1, -1, -1)),
            (0, -1, -1, -1, (0, -1, -1)),
            (3, -1, -1, 1, (4, -1, -1)),
            (4, -1, -1, -1, (3, -1, -1)),
        ]
        for job_idx, act_idx, sub_idx, delta, expected in test_cases:
            state = SelectionState(job_idx, act_idx, sub_idx)
            result = manager.new_indices_after_insert(state, delta)
            assert result == expected

    def test_is_job_selected(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, -1, -1)
        assert manager.is_job_selected()
        manager.selection_state = SelectionState(0, 0, -1)
        assert not manager.is_job_selected()

    def test_is_action_selected(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 0, -1)
        assert manager.is_action_selected()
        manager.selection_state = SelectionState(0, -1, -1)
        assert not manager.is_action_selected()

    def test_is_subaction_selected(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 0, 0)
        assert manager.is_subaction_selected()
        manager.selection_state = SelectionState(0, 0, -1)
        assert not manager.is_subaction_selected()

    def test_get_selected_job_index(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(5, 2, 1)
        assert manager.get_selected_job_index() == 5

    def test_set_selection_navigation(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        mock_nav = Mock()
        manager.set_selection_navigation(mock_nav)
        assert manager.selection_nav == mock_nav

    def test_set_enabled_all(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        mock_project = Mock()
        mock_job1 = Mock()
        mock_job2 = Mock()
        mock_project.jobs = [mock_job1, mock_job2]
        manager.project = Mock(return_value=mock_project)
        manager.mark_as_modified = Mock()
        manager.set_enabled_all(True)
        mock_job1.set_enabled_all.assert_called_once_with(True)
        mock_job2.set_enabled_all.assert_called_once_with(True)
        manager.mark_as_modified.assert_called_once_with(
            True, "Enable All", "edit_all", (-1, -1, -1))

    def test_copy_job(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, -1, -1)
        manager.element_ops = Mock()
        manager.element_ops.copy_job.return_value = Mock()
        manager.set_copy_buffer = Mock()
        manager.copy_job()
        manager.element_ops.copy_job.assert_called_once_with(0)
        manager.set_copy_buffer.assert_called_once()

    def test_copy_action(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, -1)
        manager.element_ops = Mock()
        manager.element_ops.copy_action.return_value = Mock()
        manager.set_copy_buffer = Mock()
        manager.copy_action()
        manager.element_ops.copy_action.assert_called_once_with(0, 1)
        manager.set_copy_buffer.assert_called_once()

    def test_copy_subaction(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, 2)
        manager.element_ops = Mock()
        manager.element_ops.copy_subaction.return_value = Mock()
        manager.set_copy_buffer = Mock()
        manager.copy_subaction()
        manager.element_ops.copy_subaction.assert_called_once_with(0, 1, 2)
        manager.set_copy_buffer.assert_called_once()

    def test_clone_job_success(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, -1, -1)
        manager.num_project_jobs = Mock(return_value=2)
        mock_project = Mock()
        mock_job = Mock()
        mock_job.clone.return_value = Mock()
        jobs_list = MagicMock()
        jobs_list.__getitem__ = Mock(side_effect=lambda i: [mock_job, Mock()][i])
        jobs_list.__len__ = Mock(return_value=2)
        mock_project.jobs = jobs_list
        manager.project = Mock(return_value=mock_project)
        manager.mark_as_modified = Mock()
        manager.CLONE_POSTFIX = ' (Copy)'
        result = manager.clone_job()
        assert result
        manager.mark_as_modified.assert_called_once_with(
            True, "Duplicate Job", "clone", (0, -1, -1))
        mock_job.clone.assert_called_once_with(name_postfix=' (Copy)')
        jobs_list.insert.assert_called_once_with(1, mock_job.clone.return_value)

    def test_clone_job_failure(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(5, -1, -1)
        manager.num_project_jobs = Mock(return_value=2)
        result = manager.clone_job()
        assert not result

    def test_clone_action_success(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, -1)
        manager.selection_state.widget_type = 'action'
        manager.num_project_jobs = Mock(return_value=1)
        mock_project = Mock()
        mock_job = Mock()
        mock_action = Mock()
        mock_action.clone.return_value = Mock()
        mock_job.sub_actions = [Mock(), mock_action, Mock()]
        mock_project.jobs = [mock_job]
        manager.project = Mock(return_value=mock_project)
        manager.mark_as_modified = Mock()
        result = manager.clone_action()
        assert result
        manager.mark_as_modified.assert_called_once_with(
            True, "Duplicate Action", "clone", (0, 1, -1))

    def test_clone_subaction_success(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        selection_state = SelectionState(0, 1, 2)
        with patch.object(selection_state, 'widget_type', 'subaction'):
            manager.selection_state = selection_state
            manager.num_project_jobs = Mock(return_value=1)
            mock_project = Mock()
            mock_job = Mock()
            mock_action = Mock()
            mock_action.type_name = 'combo'
            mock_subaction = Mock()
            mock_subaction.clone.return_value = Mock()
            subactions_list = MagicMock()
            subactions_list.__getitem__ = Mock(
                side_effect=lambda i: [Mock(), Mock(), mock_subaction, Mock()][i])
            subactions_list.__len__ = Mock(return_value=4)
            mock_action.sub_actions = subactions_list
            mock_job.sub_actions = [Mock(), mock_action, Mock()]
            mock_project.jobs = [mock_job]
            manager.project = Mock(return_value=mock_project)
            manager.mark_as_modified = Mock()
            manager.CLONE_POSTFIX = ' (Copy)'
            with patch(
                    'shinestacker.modern_project.modern_element_action_manager.constants') \
                    as mock_constants:
                mock_constants.ACTION_COMBO = 'combo'
                result = manager.clone_action()
                assert result
                manager.mark_as_modified.assert_called_once_with(
                    True, "Duplicate Sub-action", "clone", (0, 1, 2))
                mock_subaction.clone.assert_called_once_with(name_postfix=' (Copy)')
                subactions_list.insert.assert_called_once_with(3, mock_subaction.clone.return_value)

    def test_shift_job_success(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(1, -1, -1)
        manager.element_ops = Mock()
        manager.element_ops.shift_job.return_value = 2
        result = manager._shift_job(1)
        assert result
        manager.element_ops.shift_job.assert_called_once_with(1, 1)

    def test_shift_job_failure(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(1, -1, -1)
        manager.element_ops = Mock()
        manager.element_ops.shift_job.return_value = 1
        result = manager._shift_job(1)
        assert not result

    def test_shift_action_success(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, -1)
        manager.element_ops = Mock()
        manager.element_ops.shift_action.return_value = 2
        result = manager._shift_action(1)
        assert result
        manager.element_ops.shift_action.assert_called_once_with(0, 1, 1)

    def test_shift_subaction_success(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, 2)
        manager.element_ops = Mock()
        manager.element_ops.shift_subaction.return_value = 3
        result = manager._shift_subaction(1)
        assert result
        manager.element_ops.shift_subaction.assert_called_once_with(0, 1, 2, 1)

    def test_paste_element_no_buffer(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.has_copy_buffer = Mock(return_value=False)
        result = manager.paste_element()
        assert not result

    def test_paste_job_no_buffer(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.has_copy_buffer = Mock(return_value=False)
        result = manager.paste_job()
        assert not result

    def test_paste_action_no_buffer(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.has_copy_buffer = Mock(return_value=False)
        result = manager.paste_action()
        assert not result

    def test_paste_subaction_no_buffer(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.has_copy_buffer = Mock(return_value=False)
        result = manager.paste_subaction()
        assert not result

    def test_cut_element(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.delete_element = Mock(return_value=(Mock(), Mock(), Mock()))
        manager.set_copy_buffer = Mock()
        manager.cut_element()
        manager.delete_element.assert_called_once_with(False)
        manager.set_copy_buffer.assert_called_once()

    def test_clone_element_job(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, -1, -1)
        manager.clone_job = Mock(return_value=True)
        result = manager.clone_element()
        assert result
        manager.clone_job.assert_called_once()

    def test_clone_element_action(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, -1)
        manager.clone_action = Mock(return_value=True)
        result = manager.clone_element()
        assert result
        manager.clone_action.assert_called_once()

    def test_set_enabled_job(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, -1, -1)
        manager.num_project_jobs = Mock(return_value=1)
        mock_project = Mock()
        mock_job = Mock()
        mock_job.enabled.return_value = False
        mock_project.jobs = [mock_job]
        manager.project = Mock(return_value=mock_project)
        manager.mark_as_modified = Mock()
        manager._set_element_enabled = Mock()
        manager.set_enabled(True)
        manager.mark_as_modified.assert_called_once_with(True, "Enable Job", "edit", (0, -1, -1))
        manager._set_element_enabled.assert_called_once_with(mock_job, True, "Job")

    def test_set_enabled_action(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(0, 1, -1)
        manager.num_project_jobs = Mock(return_value=1)
        mock_project = Mock()
        mock_job = Mock()
        mock_action = Mock()
        mock_action.enabled.return_value = False
        mock_job.sub_actions = [Mock(), mock_action, Mock()]
        mock_project.jobs = [mock_job]
        manager.project = Mock(return_value=mock_project)
        manager._get_element_from_selection = Mock(return_value=mock_action)
        manager.mark_as_modified = Mock()
        manager._set_element_enabled = Mock()
        manager.set_enabled(True)
        manager.mark_as_modified.assert_called_once_with(True, "Enable Action", "edit", (0, 1, -1))
        manager._set_element_enabled.assert_called_once_with(mock_action, True, "Action")

    def test_set_enabled_invalid_selection(self):
        manager = ModernElementActionManager.__new__(ModernElementActionManager)
        manager.__init__ = Mock(return_value=None)
        manager.selection_state = SelectionState(-1, -1, -1)
        manager.set_enabled(True)
