

_days_of_the_week = ['m', 'tu', 'w', 'th', 'f', 'sa', 'su']
def get_dow_number(day_string):
    day_string = day_string.lower().strip()
    for i, dow in enumerate(_days_of_the_week):
        if day_string.startswith(dow):
            return i
    return None


def read_schedule_file(date, fname, dow=None, require_dow=True):
    import csv
    import datetime
    import re
    import cgi
    start_or_end = re.compile('([0-9]{2}):?([0-9]{2})')
    from rsab.listenagain import ListenAgainDataError

    row_number = None
    def raise_error(msg, value):
        # row_number is taken from enclosing scope
        raise ListenAgainDataError(msg, fname, row_number, value)

    reader = csv.reader(open(fname, 'r'))
    all_rows = []
    for row_number, row in enumerate(reader):
        if not row:
            continue
        if row[0] and row[0][0] in [';', '#']: # skip comments
            continue
        if len(row) < 7:
            raise_error('Row must have at least 7 (preferably 8) items', row)
        while len(row) < 9:
            row.append('')
        if len(row) > 9:
            del row[9:]

        dow_number = get_dow_number(row[0])
        if require_dow and dow_number is None:
            raise_error('Day of week is not valid', row[0])
        row[0] = dow_number
        if dow is not None and dow_number is not None and dow_number != dow:
            continue

        match = start_or_end.match(row[1])
        if match is None:
            raise_error('Start time is not in format hhmm', row[1])
        row[1] = datetime.time(*[int(x) for x in match.groups()])

        match = start_or_end.match(row[2])
        if match is None:
            raise_error('End time is not in format hhmm', row[2])
        row[2] = datetime.time(*[int(x) for x in match.groups()])

        if row[3]:
            try:
                row[3] = int(row[3])
            except ValueError:
                raise_error('Padding override (start) not int', row[3])
        else:
            row[3] = None

        if row[4]:
            try:
                row[4] = int(row[4])
            except ValueError:
                raise_error('Padding override (end) not int', row[4])
        else:
            row[4] = None

        if row[5]:
            try:
                row[5] = bool(int(row[5]))
            except ValueError:
                raise_error('Error converting record flag to bool', row[5])
        else:
            row[5] = False

        row[6] = row[6].strip().lower()

        row[7] = [x.strip() for x in row[7].lower().split(';') if x.strip()]
        while row[6] in row[7]:
            row[7].remove(row[6])

        if (not row[6] and not row[7]) or ',' in row[6]:
            raise_error('Show name is not valid', row[6])

        details = {
            'date': date,
            'start': row[1],
            'end': row[2],
            'pad_start': row[3],
            'pad_end': row[4],
            'record': row[5],
            'show': row[6],
            'presenters': row[7],
            'extra': cgi.parse_qs(row[8]),
        }
        all_rows.append( (row, details) )

    row_number = None
    all_rows.sort()
    return [details for (row, details) in all_rows]


def get_schedule(date, filter_items=None):
    import datetime
    import glob
    import os
    from rsab.listenagain import \
        config, \
        utils, \
        ListenAgainConfigError

    schedules_folder = None

    if config.has_option('main', 'schedules'):
        schedules_folder = config.get('main', 'schedules')
    if not os.path.isdir(schedules_folder):
        raise ListenAgainConfigError('Cannot find schedules folder', schedules_folder)

    schedule_file_path = None
    require_dow = True
    override_file_path = os.path.join(schedules_folder, 'override', date.strftime('%Y-%m-%d.csv'))
    if os.path.isfile(override_file_path):
        schedule_file_path = override_file_path
        require_dow = False
    if schedule_file_path is None:
        override_file_path = os.path.join(schedules_folder, 'override', date.strftime('%Y-%m-%d.txt'))
        if os.path.isfile(override_file_path):
            schedule_file_path = override_file_path
            require_dow = False
    if schedule_file_path is None:
        schedule_files_by_date = []
        for fname in glob.glob(os.path.join(schedules_folder, '*.csv')) + glob.glob(os.path.join(schedules_folder, '*.txt')):
            fname_base = os.path.splitext(os.path.split(fname)[1])[0]
            date_for_fname = utils.parse_date(fname_base)
            if date_for_fname is None:
                print 'schedule.get_schedule: Could not interpret filename as date:', fname
                continue
            schedule_files_by_date.append( (date_for_fname, fname) )
        schedule_files_by_date.sort()
        schedule_file_path = None
        for date_for_fname, try_schedule_file_path in schedule_files_by_date:
            # Later date: don't change the file we've already remembered, as
            # it's the latest one before the current date.  Break.
            if date_for_fname > date:
                break
            # The file's date is less than or equal to the date we want.  Keep
            # this file as a candidate for the schedule.
            schedule_file_path = try_schedule_file_path
            # Exact date: keep the file and break.  XXX I suspect we don't need
            # this clause as it will all work anyway, but let's be explicit...
            if date_for_fname == date:
                break
    if schedule_file_path is None:
        schedule_from_file = []
    else:
        schedule_from_file = read_schedule_file(
            date,
            schedule_file_path,
            dow=date.weekday(),
            require_dow=require_dow,
        )

    pad_start = pad_end = 0
    if config.has_option('main', 'padstart'):
        pad_start = config.getint('main', 'padstart')
    if config.has_option('main', 'padend'):
        pad_end = config.getint('main', 'padend')

    schedule = []
    for details in schedule_from_file:
        if filter_items:
            for filter_item in filter_items:
                if filter_item == details['show'] \
                or filter_item in details.get('presenters', []):
                    break
            else:
                continue
        if details.get('pad_start') is None:
            details['pad_start'] = pad_start
        if details.get('pad_end') is None:
            details['pad_end'] = pad_end
        schedule.append(details)

    return schedule


def print_schedule(schedule_list):
    if not schedule_list:
        print '(Schedule is empty)'
        return

    for details in schedule_list:
        print get_schedule_item_as_string(details)


def get_schedule_item_as_string(details):
    # XXX This looks rubbish but it will do...
    components = [
        details['start'].strftime('%H:%M:%S'),
        '(-%4.ds)' % details.get('pad_start', 0),
        details['end'].strftime('%H:%M:%S'),
        '(+%4.ds)' % details.get('pad_end', 0),
        '%-20s' % details['show'],
        ','.join(details.get('presenters', [])),
    ]
    lines = [' '.join(components)]
    if details.get('extra', {}):
        for k, v in details['extra'].items():
            lines.append(' > %s: %s' % (k, v))
    return '\n'.join(lines)


def schedule_from_audio_file_name(fname):
    import datetime
    import os.path
    import re
    import cgi
    pattern = re.compile('''
        (?P<y>[0-9]{4})(?P<m>[0-9]{2})(?P<d>[0-9]{2})
        _
        (?P<sh>[0-9]{2})(?P<sm>[0-9]{2})(?P<ss>[0-9]{2})
        _
        (?P<eh>[0-9]{2})(?P<em>[0-9]{2})(?P<es>[0-9]{2})
        _
        (?P<show>[0-9a-zA-Z-]*)
        (?P<presenters>(?:,(?:[0-9a-zA-Z-]+))*)
        (?:_(?P<extra>.+))?\\.(?P<ext>[^.]+)
        ''',
        re.VERBOSE
    )

    match = pattern.match(os.path.split(fname)[1])
    if match is None:
        return None

    groups = match.groups()
    if groups[11] is not None:
        extra = cgi.parse_qs(groups[11])
    else:
        extra = {}
    schedule_dict = {
        'date': datetime.date(int(groups[0]), int(groups[1]), int(groups[2])),
        'start': datetime.time(int(groups[3]), int(groups[4]), int(groups[5])),
        'end': datetime.time(int(groups[6]), int(groups[7]), int(groups[8])),
        'record': False,
        'show': groups[9].strip(),
        'presenters': filter(None, [p.strip() for p in groups[10].split(',')]),
        'extra': extra,
    }
    return schedule_dict

