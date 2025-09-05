# pylint: disable=C0114, C0115, C0116, R0917, R0913, R0902, W0718
import time
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from .. config.constants import constants
from .. config.config import config
from .colors import color_str
from .logging import setup_logging
from .core_utils import make_tqdm_bar, make_chunks
from .exceptions import RunStopException

LINE_UP = "\r\033[A"
TRAILING_SPACES = " " * 50


class TqdmCallbacks:
    _instance = None

    callbacks = {
        'step_counts': lambda id, name, counts: TqdmCallbacks.instance().step_counts(name, counts),
        'begin_steps': lambda id, name: TqdmCallbacks.instance().begin_steps(name),
        'end_steps': lambda id, name: TqdmCallbacks.instance().end_steps(),
        'after_step': lambda id, name, steps: TqdmCallbacks.instance().after_step()
    }

    def __init__(self):
        self.tbar = None
        self.total_action_counts = -1

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TqdmCallbacks()
        return cls._instance

    def step_counts(self, name, counts):
        self.total_action_counts = counts
        self.tbar = make_tqdm_bar(name, self.total_action_counts)

    def begin_steps(self, name):
        pass

    def end_steps(self):
        if self.tbar is None:
            raise RuntimeError("tqdm bar not initialized")
        self.tbar.close()
        self.tbar = None

    def after_step(self):
        self.tbar.write("")
        self.tbar.update(1)


tqdm_callbacks = TqdmCallbacks()


def elapsed_time_str(start):
    dt = time.time() - start
    mm = int(dt // 60)
    ss = dt - mm * 60
    hh = mm // 60
    mm -= hh * 60
    return f"{hh:02d}:{mm:02d}:{ss:05.2f}s"


class TaskBase:
    def __init__(self, name, enabled=True):
        self.id = -1
        self.name = name
        self.enabled = enabled
        self.base_message = ''
        self.logger = None
        self._t0 = None
        self.callbacks = None
        if config.JUPYTER_NOTEBOOK:
            self.begin_r, self.end_r = "", "\r"
        else:
            self.begin_r, self.end_r = LINE_UP, None

    def callback(self, key, *args):
        if self.callbacks is not None:
            callback = self.callbacks.get(key, None)
            if callback:
                return callback(*args)
        return None

    def run_core(self):
        pass

    def run(self):
        self._t0 = time.time()
        if not self.enabled:
            self.get_logger().warning(color_str(self.name + ": entire job disabled",
                                                constants.LOG_COLOR_ALERT))
        self.callback(constants.CALLBACK_BEFORE_ACTION, self.id, self.name)
        self.run_core()
        self.callback(constants.CALLBACK_AFTER_ACTION, self.id, self.name)
        msg_name = color_str(self.name + ":", constants.LOG_COLOR_LEVEL_JOB, "bold")
        msg_time = color_str(f"elapsed time: {elapsed_time_str(self._t0)}",
                             constants.LOG_COLOR_LEVEL_JOB)
        msg_completed = color_str("completed", constants.LOG_COLOR_LEVEL_JOB)
        self.get_logger().info(msg=f"{msg_name} {msg_time}{TRAILING_SPACES}")
        self.get_logger().info(msg=f"{msg_name} {msg_completed}{TRAILING_SPACES}")

    def get_logger(self, tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        if self.logger is None:
            return logging.getLogger("tqdm" if tqdm else __name__)
        return self.logger

    def set_terminator(self, tqdm=False, end='\n'):
        if config.DISABLE_TQDM:
            tqdm = False
        if end is not None:
            logging.getLogger("tqdm" if tqdm else None).handlers[0].terminator = end

    def print_message(self, msg='', level=logging.INFO, end=None, begin='', tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        self.base_message = color_str(self.name, constants.LOG_COLOR_LEVEL_1, "bold")
        if msg != '':
            self.base_message += (': ' + msg)
        self.set_terminator(tqdm, end)
        col_str = color_str(self.base_message, constants.LOG_COLOR_LEVEL_1, "bold")
        self.get_logger(tqdm).log(
            level=level,
            msg=f"{begin}{col_str}{TRAILING_SPACES}"
        )
        self.set_terminator(tqdm)

    def sub_message(self, msg, level=logging.INFO, end=None, begin='', tqdm=False):
        if config.DISABLE_TQDM:
            tqdm = False
        self.set_terminator(tqdm, end)
        self.get_logger(tqdm).log(
            level=level,
            msg=f"{begin}{self.base_message}{msg}{TRAILING_SPACES}"
        )
        self.set_terminator(tqdm)

    def print_message_r(self, msg='', level=logging.INFO):
        self.print_message(msg, level, self.end_r, self.begin_r, False)

    def sub_message_r(self, msg='', level=logging.INFO):
        self.sub_message(msg, level, self.end_r, self.begin_r, False)


class Job(TaskBase):
    def __init__(self, name, logger_name=None, log_file='', callbacks=None, **kwargs):
        TaskBase.__init__(self, name, **kwargs)
        self.action_counter = 0
        self.__actions = []
        if logger_name is None:
            setup_logging(log_file=log_file)
        if logger_name is not None:
            self.logger = logging.getLogger(logger_name)
        self.callbacks = TqdmCallbacks.callbacks if callbacks == 'tqdm' else callbacks

    def time(self):
        return time.time() - self._t0

    def init(self, a):
        pass

    def add_action(self, a: TaskBase):
        a.id = self.action_counter
        self.action_counter += 1
        a.logger = self.logger
        a.callbacks = self.callbacks
        self.init(a)
        self.__actions.append(a)

    def run_core(self):
        for a in self.__actions:
            if not (a.enabled and self.enabled):
                z = []
                if not a.enabled:
                    z.append("action")
                if not self.enabled:
                    z.append("job")
                msg = " and ".join(z)
                self.get_logger().warning(color_str(a.name + f": {msg} disabled",
                                                    constants.LOG_COLOR_ALERT))
            else:
                if self.callback(constants.CALLBACK_CHECK_RUNNING,
                                 self.id, self.name) is False:
                    raise RunStopException(self.name)
                a.run()


class SequentialTask(TaskBase):
    def __init__(self, name, enabled=True, **kwargs):
        self.max_threads = kwargs.pop('max_threads', constants.DEFAULT_MAX_FWK_THREADS)
        self.chunk_submit = kwargs.pop('chunk_submit', constants.DEFAULT_MAX_FWK_CHUNK_SUBMIT)
        TaskBase.__init__(self, name, enabled, **kwargs)
        self.total_action_counts = None
        self.current_action_count = None
        self.begin_steps = 0

    def set_counts(self, counts):
        self.total_action_counts = counts
        self.callback(constants.CALLBACK_STEP_COUNTS,
                      self.id, self.name, self.total_action_counts)

    def add_begin_steps(self, steps):
        self.begin_steps += steps

    def begin(self):
        self.callback(constants.CALLBACK_BEGIN_STEPS, self.id, self.name)

    def end(self):
        self.callback(constants.CALLBACK_END_STEPS, self.id, self.name)

    def __iter__(self):
        self.current_action_count = 0
        return self

    def run_step(self, action_count=-1):
        pass

    def __next__(self):
        if self.current_action_count < self.total_action_counts:
            self.run_step(self.current_action_count)
            x = self.current_action_count
            self.current_action_count += 1
            return x
        raise StopIteration

    def check_running(self):
        if self.callback(constants.CALLBACK_CHECK_RUNNING,
                         self.id, self.name) is False:
            raise RunStopException(self.name)

    def after_step(self, step=-1):
        if step == -1:
            step = self.current_action_count + self.begin_steps
        self.callback(constants.CALLBACK_AFTER_STEP, self.id, self.name, step)

    def run_core_serial(self):
        for _ in iter(self):
            self.after_step()
            self.check_running()

    def idx_tot_str(self, idx):
        return f"{idx + 1}/{self.total_action_counts}"

    def run_core_parallel_single_chunk(self, idx_chunk):
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            future_to_index = {}
            for idx in idx_chunk:
                self.print_message(color_str(
                    f"submit processing step: {self.idx_tot_str(idx)}",
                    constants.LOG_COLOR_LEVEL_1))
                future = executor.submit(self.run_step, idx)
                future_to_index[future] = idx
                self.check_running()
            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                try:
                    result = future.result()
                    if result:
                        self.print_message(color_str(
                            f"completed processing step: {self.idx_tot_str(idx)}",
                            constants.LOG_COLOR_LEVEL_1))
                    else:
                        self.print_message(color_str(
                            f"failed processing step: {self.idx_tot_str(idx)}",
                            constants.LOG_COLOR_WARNING))
                    self.current_action_count += 1
                    self.after_step()
                    self.check_running()
                except RunStopException as e:
                    raise e
                except Exception as e:
                    traceback.print_tb(e.__traceback__)
                    self.print_message(color_str(
                        f"failed processing step: {idx + 1}: {str(e)}",
                        constants.LOG_COLOR_ALERT))

    def run_core_parallel(self):
        self.current_action_count = 0
        self.run_core_parallel_single_chunk(list(range(self.total_action_counts)))

    def run_core_parallel_chunks(self):
        self.current_action_count = 0
        action_idx_list = list(range(self.total_action_counts))
        max_chunck_size = self.max_threads
        action_idx_chunks = make_chunks(action_idx_list, max_chunck_size)
        for idx_chunk in action_idx_chunks:
            self.run_core_parallel_single_chunk(idx_chunk)

    def run_core(self):
        self.print_message(color_str('begin run', constants.LOG_COLOR_LEVEL_2), end='\n')
        self.begin()
        if self.run_sequential():
            self.run_core_serial()
        else:
            if self.chunk_submit:
                self.run_core_parallel_chunks()
            else:
                self.run_core_parallel()
        self.end()

    def sequential_processing(self):
        return False

    def run_sequential(self):
        return self.sequential_processing() or self.max_threads == 1
