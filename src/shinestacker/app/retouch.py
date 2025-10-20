# pylint: disable=C0114, C0115, C0116, C0413, E0611, R0903, E1121, W0201
import sys
import argparse
from PySide6.QtWidgets import QApplication, QMenu
from PySide6.QtCore import QEvent
from shinestacker.config.config import config
config.init(DISABLE_TQDM=True, DONT_USE_NATIVE_MENU=True)
from shinestacker.config.constants import constants
from shinestacker.retouch.image_editor_ui import ImageEditorUI
from shinestacker.app.gui_utils import fill_app_menu
from shinestacker.app.help_menu import add_help_action
from shinestacker.app.open_frames import open_frames
from shinestacker.app.args_parser_opts import (
    add_retouch_arguments, extract_positional_filename,
    setup_filename_argument, process_filename_argument
)
from shinestacker.app.gui_utils import make_app


class RetouchApp(ImageEditorUI):
    def __init__(self):
        super().__init__()
        self.app_menu = self.create_menu()
        self.menuBar().insertMenu(self.menuBar().actions()[0], self.app_menu)
        add_help_action(self)

    def create_menu(self):
        app_menu = QMenu(constants.APP_STRING)
        fill_app_menu(self, app_menu, False, True,
                      lambda: None,
                      self.handle_config)
        return app_menu


class Application(QApplication):
    def event(self, event):
        if event.type() == QEvent.Quit and event.spontaneous():
            self.editor.quit()
        return super().event(event)


def main():
    positional_filename, filtered_args = extract_positional_filename()
    parser = argparse.ArgumentParser(
        prog=f'{constants.APP_STRING.lower()}-retouch',
        description='Final retouch focus stack image from individual frames.',
        epilog=f'This app is part of the {constants.APP_STRING} package.')
    setup_filename_argument(parser, use_const=True)
    add_retouch_arguments(parser)
    args = vars(parser.parse_args(filtered_args))
    filename = process_filename_argument(args, positional_filename)
    path = args['path']
    if filename and path:
        print("can't specify both arguments --filename and --path", file=sys.stderr)
        sys.exit(1)
    app = make_app(Application)
    editor = RetouchApp()
    app.editor = editor
    editor.show()
    if args['view_overlaid']:
        editor.set_strategy('overlaid')
    elif args['view_side_by_side']:
        editor.set_strategy('sidebyside')
    elif args['view_top_bottom']:
        editor.set_strategy('topbottom')
    open_frames(editor, filename, path)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
