# perf.py  29/01/2023  D.J.Whale - simple performance monitor toolkit
# works on HOST and PICO (using deps)
PERF_ON = False

#IDEA: could put the perf on/off check inside the decorators

deps = None
def set_deps(d) -> None:
    global deps
    deps = d

def traceall(fn:callable) -> callable:
    def wrap_traceall(*args, **kwargs):
        print("call:%s" % str(fn))
        for a in args:
            print("arg:%s" % str(a))
        for k,v in kwargs:
            print("kwarg %s=%s" % (str(k), str(v)))
        ret = fn(*args, **kwargs)
        print("  return=%s" % str(ret))
        return ret
    return wrap_traceall

def tracecall(fn:callable) -> callable:
    def wrap_tracecall(*args, **kwargs):
        print("call:%s" % str(fn))
        return fn(*args, **kwargs)
    return wrap_tracecall

def do_measure(*args) -> callable:
    """decorator: Collect performance stats about the provided function"""
    # a no-parameter decorator, and a parameter-decorator
    def decorator_perf(fn:callable) -> callable:
        class MStats:
            def __init__(self):
                self.calls = 0
                self.minrun = None
                self.maxrun = None
                self.cumrun = 0

            def update(self, runtime: int) -> None:
                self.calls += 1
                if self.minrun is None or runtime < self.minrun: self.minrun = runtime
                if self.maxrun is None or runtime > self.maxrun: self.maxrun = runtime
                self.cumrun += runtime

            def __repr__(self) -> str:
                return f"measure: calls:{self.calls} min:{self.minrun:<,} max:{self.maxrun:<,} cum:{self.cumrun:<,}"

        def wrapper_perf(*fnargs, **fnkwargs):
            ##fn_name = fn.__name__
            fn_name = str(fn)
            #TODO: need to make this run quicker
            if args[0] is not None and not callable(args[0]):
                name = "%s.%s" % (args[0], fn_name)
            else:
                name = fn_name

            try:  # single look-up optimised
                stats = perfs[name]
            except KeyError:
                stats = perfs[name] = MStats()

            start_time = deps.time_perf_time()
            res = fn(*fnargs, **fnkwargs)
            end_time = deps.time_perf_time()
            stats.update(end_time - start_time)

            return res

        return wrapper_perf

    if callable(args[0]):  #  @perf
        return decorator_perf(args[0])
    else:
        return decorator_perf  #@perf(name)

def do_tbc(fn:callable) -> callable:
    """decorator: Time between calls"""
    # just a no-parameter decorator
    def tbc_wrapper(*args, **kwargs):
        class Stats:
            def __init__(self):
                self.last_call_time = None
                self.mincall = None
                self.maxcall = None

            def just_called(self):
                now = deps.time_perf_time()

                if self.last_call_time is not None:
                    duration = now - self.last_call_time
                    if self.mincall is None or duration < self.mincall: self.mincall = duration
                    if self.maxcall is None or duration > self.maxcall: self.maxcall = duration

            def just_returning(self):
                self.last_call_time = deps.time_perf_time()

            def __repr__(self) -> str:
                return "mincall:%s maxcall:%s" % (str(self.mincall), str(self.maxcall))

        key = fn
        if key in perfs:
            stats = perfs[key]
            stats.just_called()
        else:
            stats = perfs[key] = Stats()

        # call the actual user function
        res = fn(*args, **kwargs)

        stats.just_returning()
        return res

    return tbc_wrapper

def do_dummy(*args, **kwargs) -> callable:
    """A dummy wrapper that supports params and no-params modes"""
    _ = kwargs  # argused
    if callable(args[0]): return args[0]
    def wrap(fn:callable) -> callable:
        return fn
    return wrap

def dump() -> None:
    if len(perfs) > 0:
        for name,stats in perfs.items():
            print(name, stats)
            # NOTE: if we want average time, we will have to wrap ncalls, tot_time
            # in a class, and provide a __repr__ for it
            #    ncalls, tot_time = stats
            #    avg_time = tot_time / ncalls
            #    print(f"{name: <70} {ncalls:<8} {tot_time:<15,} {avg_time:<,}")

# import utime
# import gc
#
# prev = gc.mem_free()
#
# def mem_mon_task() -> bool:
#     global prev
#     new = gc.mem_free()
#     print(prev-new)
#     prev = new
#     return True  # keep running


if PERF_ON:
    perfs = {}
    try:
        import atexit  # HOST ONLY
        atexit.register(dump)
    except ImportError:
        print("no atexit, remember to print(dttk.perfs) atend")

    measure = do_measure
    tbc     = do_tbc

    print("perf is ON")
else:
    measure = do_dummy
    tbc     = do_dummy

#END: perf.py
