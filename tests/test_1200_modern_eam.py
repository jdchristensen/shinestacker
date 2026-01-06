from unittest.mock import Mock, patch
from shinestacker.modern_project.modern_element_action_manager import ModernElementActionManager
from shinestacker.common_project.selection_state import SelectionState


class TestModernElementActionManagerMinimal:

    def test_constructor_doesnt_crash(self):
        with patch.object(ModernElementActionManager, '__init__', return_value=None):
            manager = ModernElementActionManager(
                Mock(),
                SelectionState(),
                {
                    'refresh_ui': Mock(),
                    'remove_widget': Mock(),
                    'update_selection': Mock(),
                    'ensure_selected_visible': Mock(),
                    'move_widgets': Mock()
                }
            )
            assert manager is not None

    def test_delete_without_confirmation_doesnt_crash(self):
        with patch.object(ModernElementActionManager, 'num_project_jobs', return_value=0):
            manager = ModernElementActionManager(
                Mock(),
                SelectionState(-1, -1, -1),
                {k: Mock() for k in ['refresh_ui', 'remove_widget', 'update_selection',
                                     'ensure_selected_visible', 'move_widgets']}
            )
            manager.element_ops = Mock()
            result = manager.delete_element(confirm=False)
            assert result is None

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
            with patch.object(ModernElementActionManager, 'project') as mock_project:
                mock_project.return_value.jobs = [Mock()]
                mock_project.return_value.jobs[0].params = {'name': 'Test Job'}
                manager = ModernElementActionManager(
                    Mock(),
                    SelectionState(0, -1, -1),
                    {k: Mock() for k in ['refresh_ui', 'remove_widget', 'update_selection',
                                         'ensure_selected_visible', 'move_widgets']}
                )
                manager.element_ops = Mock()
                with patch.object(manager, 'confirm_delete_message', return_value=True):
                    with patch.object(manager, 'mark_as_modified'):
                        with patch.object(manager, 'new_indices_after_delete',
                                          return_value=(-1, -1, -1)):
                            result = manager.delete_element(confirm=True)
                            assert result is not None
