import logging
from shinestacker.core.colors import color_str
from shinestacker.core.logging import setup_logging
from shinestacker.config.constants import constants
from shinestacker.algorithms.stack_framework import StackJob, CombinedActions, SubAction


class SubActionMock(SubAction):
    def __init__(self, noise_mask=constants.DEFAULT_NOISE_MAP_FILENAME,
                 kernel_size=constants.DEFAULT_MN_KERNEL_SIZE,
                 method=constants.INTERPOLATE_MEAN, **kwargs):
        super().__init__(**kwargs)

    def begin(self, process):
        self.process = process
        self.process.sub_message_r(color_str(': test - bagin',
                                   constants.LOG_COLOR_LEVEL_3))

    def run_frame(self, idx, _ref_idx, image):
        self.process.print_message(color_str(
            f'{self.process.frame_str(idx)}: test', constants.LOG_COLOR_LEVEL_3))
        return image


def test_combined_actions():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file=f"logs/{constants.APP_STRING.lower()}.log"
    )
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg", callbacks='tqdm')
        job.add_action(CombinedActions("test",
                                       [SubActionMock()],
                                       output_path="output/img-test-fwk"))
        job.run()
    except Exception:
        assert False


def test_combined_actions_filelist():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file=f"logs/{constants.APP_STRING.lower()}.log"
    )
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg",
                       input_filepaths=['0000.jpg', '0001.jpg'], callbacks='tqdm')
        job.add_action(CombinedActions("test",
                                       [SubActionMock()],
                                       output_path="output/img-test-fwk"))
        job.run()
    except Exception:
        assert False


def test_combined_actions_filelist_fail():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file=f"logs/{constants.APP_STRING.lower()}.log"
    )
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg",
                       input_filepaths=['0000.jpg', '00xx.jpg', '0002.jpg'], callbacks='tqdm')
        job.add_action(CombinedActions("test",
                                       [SubActionMock()],
                                       output_path="output/img-test-fwk"))
        job.run()
    except Exception:
        assert False


def test_combined_actions_filelist_fail_all():
    setup_logging(
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        log_file=f"logs/{constants.APP_STRING.lower()}.log"
    )
    try:
        job = StackJob("job", "examples/", input_path="input/img-jpg",
                       input_filepaths=['00xx.jpg', '00yy.jpg'], callbacks='tqdm')
        job.add_action(CombinedActions("test",
                                       [SubActionMock()],
                                       output_path="output/img-test-fwk"))
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_combined_actions()
    test_combined_actions_filelist_fail()
    test_combined_actions_filelist_fail_all()
