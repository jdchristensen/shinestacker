import time
import random
from shinestacker.core.colors import color_str
from shinestacker.core.framework import Job, SequentialTask


class MySequence(SequentialTask):
    def __init__(self, name, enabled=True, max_threads=4, chunk_submit=True):
        SequentialTask.__init__(
            self, name, enabled, max_threads=max_threads, chunk_submit=chunk_submit)

    def begin(self):
        super().begin()
        self.set_counts(10)

    def run_step(self, action_step):
        time.sleep(random.random() * 0.1)
        self.print_message(color_str(f"my seqence - step {action_step + 1}", "cyan"))


def test_run():
    try:
        job = Job("job")
        job.add_action(MySequence("my actions", chunk_submit=False))
        a = MySequence("my actions", enabled=False)
        job.add_action(a)
        job.run()
    except Exception:
        assert False


def test_run_chunks():
    try:
        job = Job("job - chunks")
        job.add_action(MySequence("my actions", chunk_submit=True))
        a = MySequence("my actions", enabled=False)
        job.add_action(a)
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_run()
    test_run_chunks()
