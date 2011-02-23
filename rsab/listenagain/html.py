
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
    template = Template('playlist-item')
    template.title = utils.get_show_title_string(
        details['show'],
        details.get('presenters'),
    )
    template.date = details['date'].strftime('%A %d %B %Y')
    template.start_time = details['start'].strftime('%H:%M')
    template.end_time = details['end'].strftime('%H:%M')

    duration = (
        datetime.datetime.combine(details['date'], details['end'])
        - datetime.datetime.combine(details['date'], details['start'])
    ).seconds / 60.0 # approx minutes
    if duration % 15 < 7.5:
        duration = divmod(duration, 15)[0] * 15
    else:
        duration = (divmod(duration, 15)[0] + 1) * 15
    duration_h, duration_m = divmod(duration, 60)
    if duration_m:
        duration_string = '%dh %dm' % (duration_h, duration_m)
    else:
        duration_string = '%dh' % (duration_h,)
    template.duration = duration_string

    template.url = audio_path + urllib.quote(os.path.split(audio_fname)[1])
    return template


def make_index_file(audio_fname_list, output_fname=None):
    import os
    from rsab.listenagain import config, ListenAgainConfigError
    if not config.has_option('DEFAULT', 'output'):
        raise ListenAgainConfigError('No [DEFAULT]/output config defined')

    if output_fname is None:
        output_fname = 'index.html'
    output_fname = os.path.join(config.get('DEFAULT', 'output'), output_fname)
    output_file = open(output_fname, 'w')

    template = Template('player')
    template.playlist_items = '\n'.join([
        str(make_playlist_item(audio_fname))
        for audio_fname in audio_fname_list
    ])

    output_file.write(str(template))
    output_file.close()
    return output_fname
