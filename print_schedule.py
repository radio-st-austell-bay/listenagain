
def run():
    from optparse import OptionParser
    import datetime
    import os
    import simplejson
    import sys

    from rsab.listenagain import schedule, utils

    option_parser = OptionParser("usage: %prog [options] [[FROM_DATE] TO_DATE]")
    option_parser.add_option(
        '-c',
        '--config',
        dest='config_file',
        help="Specify alternative config file",
        metavar='FILE',
    )
    option_parser.add_option(
        '--human-readable',
        dest='human_readable',
        help="Add line-breaks and indentation to the JSON output",
        action='store_true',
    )
    options, args = option_parser.parse_args()

    config_files = utils.default_config_files()
    if options.config_file is not None:
        config_files.append(options.config_file)
    config = utils.init_config(config_files)

    from_date = to_date = 'today'
    if len(args) == 0:
        pass
    elif len(args) == 1:
        to_date = args[0]
    elif len(args) == 2:
        from_date = args[0]
        to_date = args[1]
    else:
        option_parser.print_help()
        return 0

    from_date = utils.interpret_date_string(from_date)
    to_date = utils.interpret_date_string(to_date)
    if to_date < from_date:
        from_date, to_date = to_date, from_date

    results = {}
    date = from_date
    while True:
        show_list = []
        for raw_show_data in schedule.get_schedule(date):
            short_day = raw_show_data['date'].strftime('%a').lower()
            show = raw_show_data['show']
            presenters = raw_show_data['presenters']
            show_title = utils.get_message(show, 'show', default=None)
            if show_title is None:
                show_title = utils.get_message(
                    show,
                    'presenter',
                    default=show,
                )
            presenter_titles = filter(None, [
                utils.get_message(presenter, 'presenter', default=presenter)
                for presenter in presenters
                if presenter != show
            ])
            notes = []
            site_page = None
            for name in [show] + presenters:
                note = utils.get_message(name, 'note', default=None)
                if note is not None:
                    notes.append(note)
                note = utils.get_message(
                    '%s:%s' % (short_day, name),
                    'note',
                    default=None,
                )
                if note is not None:
                    notes.append(note)
                if site_page is None:
                    site_page = utils.get_message(
                        name,
                        'site_page',
                        default=None,
                    )
            show_data = {
                'date': str(raw_show_data['date']),
                'start': raw_show_data['start'].strftime('%H:%M'),
                'end': raw_show_data['end'].strftime('%H:%M'),
                'show-name': show_title,
                'presenter-names': presenter_titles,
                'notes': notes,
                'site-page': site_page,
            }
            if raw_show_data['record']:
                show_data['la-params'] = {
                    'day': [short_day],
                    'show': [show] + presenters,
                }
            show_list.append(show_data)
        results[str(date)] = {
            'la-params': {
                'day': [date.strftime('%a').lower()],
            },
            'schedule': show_list,
        }
        if date == to_date:
            break
        date += datetime.timedelta(days=1)

    if options.human_readable:
        indent = '  '
    else:
        indent = None
    print simplejson.dumps(results, indent=indent, sort_keys=True)
    return 0


if __name__ == '__main__':
    run()
