

_days_of_the_week = ['m', 'tu', 'w', 'th', 'f', 'sa', 'su']
def get_dow_number(day_string):
    day_string = day_string.lower().strip()
    for i, dow in enumerate(_days_of_the_week):
        if day_string.startswith(dow):
            return i
    return None


def read_schedule_file(fname, dow=None, require_dow=True):
    import csv
    import datetime
    import re
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
        if len(row) < 6:
            raise_error('Row must have at least 6 (preferably 7) items', row)
        if len(row) == 6:
            row.append('')
        elif len(row) > 7:
            del row[7:]

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

        row[5] = row[5].strip().lower()
        if not row[5] or ',' in row[5]:
            raise_error('Show name is not valid', row[5])

        row[6] = [x.strip() for x in row[6].lower().split(';') if x.strip()]
        while row[5] in row[6]:
            row[6].remove(row[5])

        all_rows.append(row)

    row_number = None
    all_rows.sort()
    return all_rows


def get_schedule(date):
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
        raise ListenAgainConfigError('Cannot find schedules folder', folder)

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
        for date_for_fname, schedule_file_path in schedule_files_by_date:
            if date_for_fname > date:
                break
    if schedule_file_path is None:
        schedule_from_file = []
    else:
        schedule_from_file = read_schedule_file(
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
    for record in schedule_from_file:
        if record[3] is None: # pad start
            record[3] = pad_start
        if record[4] is None: # pad end
            record[4] = pad_end
        schedule.append(record[1:]) # don't need DOW now

    return schedule


def print_schedule(schedule_list):
    if not schedule_list:
        print '(Schedule is empty)'
        return

    for schedule_item in schedule_list:
        print get_schedule_item_as_string(schedule_item)


def get_schedule_item_as_string(schedule_item):
    # XXX This looks rubbish but it will do...
    time_start, time_end, pad_start, pad_end, show, presenters = schedule_item
    components = [
        time_start.strftime('%H:%M:%S'),
        '(-%4.ds)' % pad_start,
        time_end.strftime('%H:%M:%S'),
        '(+%4.ds)' % pad_end,
        '%-20s' % show,
        ','.join(presenters),
    ]
    return ' '.join(components)


def schedule_from_audio_file_name(fname):
    import datetime
    import os.path
    import re
    pattern = re.compile('''
        (?P<y>[0-9]{4})(?P<m>[0-9]{2})(?P<d>[0-9]{2})
        _
        (?P<sh>[0-9]{2})(?P<sm>[0-9]{2})(?P<ss>[0-9]{2})
        _
        (?P<eh>[0-9]{2})(?P<em>[0-9]{2})(?P<es>[0-9]{2})
        _
        (?P<show>[0-9a-zA-Z-]+)
        (?P<presenters>(?:,(?:[0-9a-zA-Z-]+))*)
        (?:_(?P<extra>.+))?\\.(?P<ext>[^.]+)
        ''',
        re.VERBOSE
    )

    match = pattern.match(os.path.split(fname)[1])
    if match is None:
        return None

    groups = match.groups()
    schedule_dict = {
        'date': datetime.date(int(groups[0]), int(groups[1]), int(groups[2])),
        'start': datetime.time(int(groups[3]), int(groups[4]), int(groups[5])),
        'end': datetime.time(int(groups[6]), int(groups[7]), int(groups[8])),
        'show': groups[9].strip(),
        'presenters': filter(None, [p.strip() for p in groups[10].split(',')]),
        'extra': groups[11],
    }
    return schedule_dict

