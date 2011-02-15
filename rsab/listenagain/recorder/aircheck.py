
def get_files_for_date(date):
    import glob
    import os
    from rsab.listenagain import config

    folder = None
    if config.has_option('rec.aircheck', 'path'):
        folder = config.get('rec.aircheck', 'path')

    if folder is None or not os.path.isdir(folder):
        from rsab.listenagain import ListenAgainConfigError
        raise ListenAgainConfigError('Cannot find AirCheck recordings folder', folder)

    return glob.glob(os.path.join(folder, date.strftime('%Y%m%d*.wav')))


def get_bounds_and_files_for_date(date):
    import datetime
    import os
    import wave
    files = get_files_for_date(date)
    bounds_and_files = []
    for path_and_file in files:
        fname = os.path.split(path_and_file)[1]
        hhmmss = fname[8:14]
        try:
            hh, mm, ss = int(hhmmss[:2]), int(hhmmss[2:4]), int(hhmmss[4:])
        except ValueError:
            from rsab.listenagain import ListenAgainDataError
            raise ListenAgainDataError('File name not in format YYYYMMDDhhmmss.wav', path_and_file)
        start = datetime.datetime(date.year, date.month, date.day, hh, mm, ss)
        w = wave.open(path_and_file, 'rb')
        frames = w.getnframes()
        rate = w.getframerate()
        end = start + datetime.timedelta(seconds=frames/float(rate))
        w.close()
        bounds_and_files.append( (start, end, path_and_file) )

    return bounds_and_files

