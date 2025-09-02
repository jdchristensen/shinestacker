# pylint: disable=C0114, C0116, E0611
from PySide6.QtWidgets import QWidget, QPushButton, QHBoxLayout, QSizePolicy, QLineEdit


def create_layout_widget_no_margins(layout):
    layout.setContentsMargins(0, 0, 0, 0)
    container = QWidget()
    container.setLayout(layout)
    container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return container


def create_layout_widget_and_connect(button, edit, browse):
    button.clicked.connect(browse)
    button.setAutoDefault(False)
    layout = QHBoxLayout()
    layout.addWidget(edit)
    layout.addWidget(button)
    return create_layout_widget_no_margins(layout)


def create_layout_plus_button_and_connect(button, edit):
    button.setAutoDefault(False)
    layout = QHBoxLayout()
    layout.addWidget(edit)
    layout.addWidget(button)
    return create_layout_widget_no_margins(layout), button


def create_select_file_paths_widget(value, placeholder):
    edit = QLineEdit(value)
    edit.setPlaceholderText(placeholder)
    button = QPushButton("Browse...")
    button.setFixedWidth(120)
    edit.selection_mode = 'folder'
    edit.selected_files = []
    container, browse_button = create_layout_plus_button_and_connect(button, edit)
    return edit, container, browse_button
