# pylint: disable=C0114, C0116

def add_project_arguments(parser):
    parser.add_argument('-x', '--expert', action='store_true', help='''
expert options are visible by default.
''')
    parser.add_argument('-n', '--no-new-project', dest='new-project',
                        action='store_false', default=True, help='''
Do not open new project dialog at startup (default: open).
''')


def add_retouch_arguments(parser):
    parser.add_argument('-p', '--path', nargs='?', help='''
import frames from one or more directories.
Multiple directories can be specified separated by ';'.
''')
    view_group = parser.add_mutually_exclusive_group()
    view_group.add_argument('-v1', '--view-overlaid', action='store_true', help='''
set overlaid view.
''')
    view_group.add_argument('-v2', '--view-side-by-side', action='store_true', help='''
set side-by-side view.
''')
    view_group.add_argument('-v3', '--view-top-bottom', action='store_true', help='''
set top-bottom view.
''')
