
_module = None

def init_module():
    global _module
    if _module is None:
        from rsab.listenagain import config
        if config.has_option('main', 'recorder'):
            recorder_name = config.get('main', 'recorder')
        else:
            recorder_name = 'aircheck'
        # XXX Surely there's a nicer way to do this?
        try:
            recorder_package = __import__('rsab.listenagain.recorder', locals(), globals(), [recorder_name])
        except ImportError:
            from rsab.listenagain import ListenAgainConfigError
            raise ListenAgainConfigError('Invalid recorder module', recorder_name)
        else:
            _module = getattr(recorder_package, recorder_name)
        for name in dir(_module):
            if not name.startswith('_'):
                globals()[name] = getattr(_module, name)
    return _module


def print_bounds_and_files(bounds_and_files):
    if not bounds_and_files:
        print '(No recordings found)'
        return

    import os

    for time_start, time_end, path_and_file in bounds_and_files:
        print time_start.strftime('%H:%M:%S'),
        print '-',
        print time_end.strftime('%H:%M:%S'),
        print '[',
        print os.path.split(path_and_file)[1],
        print ']'


