# tasking.py  12/01/2023  D.J.Whale
# works on HOST and PICO

def run_all(tasks:list, trace:callable or None=None) -> None:
    """A generic cooperative looper"""
    while len(tasks) != 0:
        i = 0
        while i < len(tasks):
            task = tasks[i]
            # if it is a task stack, run the top task
            if isinstance(task, list):
                assert len(task) > 0, "got an empty task stack"
                task = task[-1]  # last (top) in the task stack

            if callable(task):
                res = task()
            elif hasattr(task, "tick"):
                res = task.tick()
            else:
                trace(task)
                res = None

            if res is not None:
                if isinstance(res, bool):
                    if not res:
                        # task finished
                        task = tasks[i]
                        if isinstance(task, list):
                            task.pop()  # remove topmost task from this task stack
                            if len(task) == 0:
                                tasks.pop(i)  # the whole task stack is finished
                        else:
                            # just a single task
                            tasks.pop(i)
                        continue # don't increment 'i' as we have lost a task
                else:
                    if trace: trace(str(res))
            i += 1

def test():
    class Task:
        def __init__(self, name:str, v:int):
            self._name = name
            self._v = v

        def tick(self):
            print(self._name, self._v)
            self._v -= 1
            return self._v != 0  # runs until becomes zero


    # just single tasks
    ##tasks = [Task("ten", 10), Task("five", 5), Task("one", 1)]
    ##run_all(tasks)

    # some tasks and task stats
    tasks = [Task("ten", 10), [Task("g1", 1), Task("g2", 2), Task("g3", 3)], Task("tenb", 10)]
    run_all(tasks)

# END: tasking.py

