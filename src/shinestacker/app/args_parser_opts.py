# pylint: disable=C0114, C0116
import sys


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


def extract_positional_filename():
    positional_filename = None
    filtered_args = []
    for arg in sys.argv[1:]:
        if not arg.startswith('-') and not positional_filename:
            positional_filename = arg
        else:
            filtered_args.append(arg)
    return positional_filename, filtered_args


def setup_filename_argument(parser, use_const=True):
    if use_const:
        parser.add_argument('-f', '--filename', nargs='?', const=True, help='''
filename to open. Can be a project file or image file.
Multiple files can be specified separated by ';'.
''')
    else:
        parser.add_argument('-f', '--filename', nargs='?', help='''
filename to open. Can be a project file or image file.
Multiple files can be specified separated by ';'.
''')


def process_filename_argument(args, positional_filename):
    filename = args.get('filename')
    if positional_filename and not filename:
        filename = positional_filename
    if filename is True:
        if positional_filename:
            filename = positional_filename
        else:
            print("Error: -f flag used but no filename provided", file=sys.stderr)
            sys.exit(1)
    return filename
