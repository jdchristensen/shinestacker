import time
import random
from shinestacker.config.config import config
config.init(DISABLE_TQDM=True)
from shinestacker.core.colors import color_str
from shinestacker.core.framework import Job, TaskBase, SequentialTask

class MySequence(SequentialTask):
    def __init__(self, name, enabled=True, max_threads=8):
        SequentialTask.__init__(self, name, enabled, max_threads=max_threads)

    def begin(self):
        super().begin()
        self.set_counts(10)

    def run_step(self, action_step):
        time.sleep(random.random())
        self.print_message(color_str(f"my seqence - step {action_step + 1}", "magenta"))


def test_run():
    try:
        job = Job("job", callbacks='tqdm')
        job.add_action(MySequence("my actions"))
        a = MySequence("my actions", enabled=False)
        job.add_action(a)
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_run()
