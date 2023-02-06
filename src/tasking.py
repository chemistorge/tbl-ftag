# tasking.py  12/01/2023  D.J.Whale
# works on HOST and PICO

def run_all(tasks: list, trace: callable or None = None) -> None:
    """A generic cooperative looper"""
    # last_time = utime.ticks_ms()
    while len(tasks) != 0:
        i = 0
        while i < len(tasks):
            task = tasks[i]
            if callable(task):
                res = task()
            elif hasattr(task, "tick"):
                res = task.tick()
            else:
                trace(task)
                res = None

            # now = utime.ticks_ms()
            # if trace: trace("task ran for %d ms" % (now - last_time))
            # last_time = now

            if res is not None:
                if isinstance(res, bool):
                    if not res:
                        # task finished
                        tasks.pop(i)
                        continue
                else:
                    if trace: trace(str(res))
            i += 1


def test():
    class Task():
        def __init__(self, id, output=print):
            self._id = id
            self._output = output

        def tick(self):
            if self._output is not None: self._output("t%d" % self._id)
            return True

    run_all([Task(1), Task(2)], print)

# END: tasking.py

