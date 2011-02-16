
def default_config_files():
    import os
    import rsab.listenagain

    config_list = []

    default_file = os.path.join(os.path.split(rsab.listenagain.__file__)[0], 'default.ini')
    if os.path.isfile(default_file):
        config_list.append(default_file)

    cwd = os.getcwd()
    file_here = os.path.join(cwd, 'config.ini')
    if os.path.isfile(file_here):
        config_list.append(file_here)

    return config_list


def init_config(config_files=None):
    import rsab.listenagain
    if config_files is None:
        config_files = default_config_files()
    if rsab.listenagain.config is None:
        from ConfigParser import SafeConfigParser
        rsab.listenagain.config = SafeConfigParser()
        rsab.listenagain.config.read(config_files)

    return rsab.listenagain.config


def parse_date(date_string):
    import datetime
    import re
    match = re.match('^([0-9]{4})-?([0-9]{2})-?([0-9]{2})', date_string)
    if match is None:
        date = None
    else:
        date = datetime.date(*[int(x) for x in match.groups()])
    return date


def interpret_date_string(date_string):
    import datetime
    date_string = date_string.lower().strip()
    if date_string == 'yesterday':
        date = datetime.date.today()
        date -= datetime.timedelta(days=1)
    elif date_string == 'today':
        date = datetime.date.today()
    else:
        date = parse_date(date_string)
        if date is None:
            from rsab.listenagain import ListenAgainUsageError
            raise ListenAgainUsageError('Date must be "yesterday", "today" or YYYY-MM-DD', date_string)
    return date


def apply_padding(time, pad, subtract=False):
    import datetime
    time_with_date = datetime.datetime.combine(datetime.date.today(), time)
    delta = datetime.timedelta(seconds=pad)
    if subtract:
        time_with_date -= delta
    else:
        time_with_date += delta
    return time_with_date.time()


def format_large_number(n):
    s = str(n)
    if '.' in s:
        s, rest = s.split('.', 1)
    else:
        rest = ''
    SEP = ','
    WIDTH = 3
    parts = []
    upper = len(s)
    while upper > 0:
        lower = upper - WIDTH
        if lower < 0:
            lower = 0
        parts.append(s[lower:upper])
        upper -= WIDTH
    parts.reverse()
    s = SEP.join(parts)
    if rest:
        s += '.' + rest
    return s


def parse_audio_file_name(fname):
    import datetime
    import os
    fname = os.path.splitext(os.path.split(fname)[1])[0]
    parts = fname.split('_')
    if len(parts) not in [4, 5]:
        return None
    if len(parts) == 4:
        parts.append(None)
    details = {}
    if len(parts[0]) == 8:
        try:
            year, month, day = int(parts[0][:4]), int(parts[0][4:6]), int(parts[0][6:])
        except ValueError:
            pass
        else:
            details['date'] = datetime.date(year, month, day)
    if len(parts[1]) == 6:
        try:
            hour, minute, second = int(parts[1][:2]), int(parts[1][2:4]), int(parts[1][4:])
        except ValueError:
            pass
        else:
            details['start'] = datetime.time(hour, minute, second)
    if len(parts[2]) == 6:
        try:
            hour, minute, second = int(parts[2][:2]), int(parts[2][2:4]), int(parts[2][4:])
        except ValueError:
            pass
        else:
            details['end'] = datetime.time(hour, minute, second)
    show = parts[3].split(',')
    if show:
        details['show'] = show[0]
        details['presenters'] = show[1:]
    details['extra'] = parts[4]

    for key in ['date', 'start', 'end', 'show']:
        if details.get(key) is None:
            return None

    return details

def schedule_from_audio_file_name(fname):
    import re
    pattern = re.compile('''
        (?P<y>[0-9]{4})(?P<m>[0-9]{2})(?P<d>[0-9]{2})
        _
        (?P<sh>[0-9]{2})(?P<sm>[0-9]{2})(?P<ss>[0-9]{2})
        _
        (?P<eh>[0-9]{2})(?P<em>[0-9]{2})(?P<es>[0-9]{2})
        _
        (?P<show>[0-9a-zA-Z-]+)
        (?:,(?P<presenters>[0-9a-zA-Z-]+))*
        (?:_(?P<extra>.+))?\\.(?P<ext>[^.]+)
        ''',
        re.VERBOSE
    )
    # XXX Better check this!  We should be able to build a Schedule object from
    # it, though.

