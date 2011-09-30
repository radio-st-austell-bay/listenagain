
class Template:

    def __init__(self, name, data=None, default=None):
        self.__dict__['_template'] = self._find_template(name)
        my_data = {}
        if data is not None:
            my_data.update(data)
        self.__dict__['_data'] = my_data
        self.__dict__['_default'] = default


    def _find_template(self, name):
        import glob
        import os
        from rsab.listenagain import config, ListenAgainConfigError
        if not config.has_option('main', 'templates'):
            raise ListenAgainConfigError('No [main]/templates config defined')
        template_dir = config.get('main', 'templates')
        fname = os.path.join(template_dir, name)
        if os.path.exists(fname):
            return fname
        fnames = glob.glob(os.path.join(template_dir, name + '.*'))
        if fnames:
            return fnames[0] # XXX Better choice?
        return None


    def __setattr__(self, key, value):
        self.__dict__['_data'][key] = value


    def __str__(self):
        if self._template is None:
            template = ''
        else:
            template = open(self._template, 'r').read()
        default = self._default
        data = {}
        data.update(self._data)
        while 1:
            try:
                return template % data
            except KeyError, key_error:
                key = key_error.args[0]
                if default is None:
                    data[key] = '!!!Missing: [%s]!!!' % (key,)
                else:
                    data[key] = default


def make_playlist_item(audio_fname):
    import datetime
    import os
    import urllib

    from rsab.listenagain import config, ListenAgainConfigError
    import schedule
    import utils

    if not config.has_option('ftp', 'audio_path'):
        raise ListenAgainConfigError('Missing option', 'ftp', 'audio_path')
    audio_path = config.get('ftp', 'audio_path')
    if not audio_path.endswith('/'):
        audio_path += '/'

    details = schedule.schedule_from_audio_file_name(audio_fname)
    if details is None or details['show'].startswith('xx'):
        return ''
    template = Template('playlist-item')
    template.title = utils.get_show_title_string(
        details['show'],
        details.get('presenters'),
    )
    template.date = details['date'].strftime('%a %d %b %Y')
    template.date_compact = details['date'].strftime('%Y%m%d')
    template.day_short = details['date'].strftime('%a').lower()
    template.start_time = details['start'].strftime('%H:%M')
    template.start_compact = details['start'].strftime('%H%M')
    template.end_time = details['end'].strftime('%H:%M')
    template.end_compact = details['end'].strftime('%H%M')

    duration = (
        datetime.datetime.combine(details['date'], details['end'])
        - datetime.datetime.combine(details['date'], details['start'])
    ).seconds / 60.0 # approx minutes
    ROUND_TO_MINUTES = 1
    if duration % ROUND_TO_MINUTES < (ROUND_TO_MINUTES / 2.0):
        duration = divmod(duration, ROUND_TO_MINUTES)[0] * ROUND_TO_MINUTES
    else:
        duration = (divmod(duration, ROUND_TO_MINUTES)[0] + 1) * ROUND_TO_MINUTES
    duration_h, duration_m = divmod(duration, 60)
    if duration_m:
        duration_string = '%dh %dm' % (duration_h, duration_m)
    else:
        duration_string = '%dh' % (duration_h,)
    template.duration = duration_string

    hidden_input = '<input type="hidden" disabled="disabled" name="%s" value="%s" />'
    template.show_names = hidden_input % ('show', details['show'])
    template.presenter_names = '\n'.join([
        hidden_input % ('presenter', presenter)
        for presenter in details.get('presenters', [])
        if presenter and presenter != details['show']
    ])

    template.url = audio_path + urllib.quote(os.path.split(audio_fname)[1])
    return template


def make_index_file(date, audio_fname_list, output_fname=None):
    import datetime
    import os

    import schedule
    import utils
    from rsab.listenagain import config, ListenAgainConfigError
    if not config.has_option('DEFAULT', 'output'):
        raise ListenAgainConfigError('No [DEFAULT]/output config defined')

    if output_fname is None:
        output_fname = 'index.html'
    output_fname = os.path.join(config.get('DEFAULT', 'output'), output_fname)
    output_file = open(output_fname, 'w')

    template = Template('player')

    playlist_items = []
    details_for_audio_files = []
    show_name_mapping = {}
    presenter_name_mapping = {}
    for audio_fname in audio_fname_list:
        playlist_items.append(str(make_playlist_item(audio_fname)))
        details_for_audio_files.append(schedule.schedule_from_audio_file_name(audio_fname))

    live_schedule = schedule.get_schedule(date + datetime.timedelta(days=1))
    for details in details_for_audio_files + live_schedule:
        if details is None:
            continue
        show_name = details['show']
        show_title = utils.get_message(show_name, 'show', default=None)
        if show_title is None:
            show_title = utils.get_message(show_name, 'presenter', default=show_name)
        if show_name and show_name not in show_name_mapping:
            show_name_mapping[show_name] = show_title
        for presenter in details.get('presenters', []):
            if not presenter or presenter == show_name:
                continue
            if presenter not in presenter_name_mapping:
                presenter_name_mapping[presenter] = utils.get_message(presenter, 'presenter', default=presenter)

    template.playlist_items = '\n'.join(filter(None, playlist_items))
    hidden_input = '<input type="hidden" disabled="disabled" name="%s" value="%s" />'
    template.show_name_mapping = '\n'.join([
        hidden_input % ('showname', '%s:%s' % pair)
        for pair in show_name_mapping.items()
    ])
    template.presenter_name_mapping = '\n'.join([
        hidden_input % ('presentername', '%s:%s' % pair)
        for pair in presenter_name_mapping.items()
    ])
    template.live_schedule = '\n'.join([
        hidden_input % (
            'live_schedule',
            '%s:%s' % (
                details['start'].strftime('%H:%M'),
                ','.join([details['show']] + details.get('presenters', [])),
            ),
        )
        for details in schedule.get_schedule(date + datetime.timedelta(days=1))
    ])

    output_file.write(str(template))
    output_file.close()
    return output_fname
