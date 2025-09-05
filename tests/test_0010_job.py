import time
from shinestacker.core.colors import color_str
from shinestacker.core.framework import Job, TaskBase, SequentialTask


class Action1(TaskBase):
    def __init__(self):
        TaskBase.__init__(self, "action 1")

    def run(self):
        self.print_message(color_str("run 1", "blue", "bold"))
        time.sleep(0.1)


class Action2(TaskBase):
    def __init__(self):
        TaskBase.__init__(self, "action 2")

    def run(self):
        self.print_message(color_str("run 2", "blue", "bold"))
        time.sleep(0.1)


class MySequence(SequentialTask):
    def __init__(self, name, enabled=True):
        SequentialTask.__init__(self, name, enabled=enabled)

    def begin(self):
        super().begin()
        self.set_counts(10)

    def run_step(self, action_step):
        self.print_message_r(color_str("action: {}".format(action_step + 1), "blue"))
        time.sleep(0.1)


def test_run():
    try:
        job = Job("job", callbacks='tqdm')
        job.add_action(Action1())
        job.add_action(Action2())
        job.add_action(MySequence("my actions"))
        a = MySequence("my actions", enabled=False)
        job.add_action(a)
        job.run()
    except Exception:
        assert False


if __name__ == '__main__':
    test_run()
