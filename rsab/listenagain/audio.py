
# XXX Going to just start writing then refactor later...
def make_wav_files(date, bounds_and_files, schedule_list):
    import datetime
    import os
    import wave
    from rsab.listenagain import config, schedule, utils
    if config.has_option('main', 'wavs'):
        output_dir = config.get('main', 'wavs')
    else:
        output_dir = os.getcwd()

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if not bounds_and_files:
        return None
    wav_reader = wave.open(bounds_and_files[0][2], 'rb')
    output_wav_params = wav_reader.getparams()
    output_wav_params = list(output_wav_params)
    output_wav_params[3] = 0
    output_wav_params = tuple(output_wav_params)
    wav_reader.close()

    frame_rate = output_wav_params[2]
    frame_size = output_wav_params[0] + output_wav_params[1]
    if config.has_option('main', 'framechunksize'):
        frame_chunk = config.getint('main', 'framechunksize')
    else:
        frame_chunk = 65536

    print 'Reading audio data in chunks of', utils.format_large_number(frame_chunk), 'frames'
    print 'Output directory:', output_dir

    output_wav_files = []
    bounds_and_files.sort()
    for schedule_item in schedule_list:
        time_start, time_end, pad_start, pad_end, show, presenters = schedule_item
        actual_time_start = utils.apply_padding(time_start, pad_start, subtract=True)
        actual_time_start = datetime.datetime.combine(date, actual_time_start)
        actual_time_end = utils.apply_padding(time_end, pad_end, subtract=False)
        actual_time_end = datetime.datetime.combine(date, actual_time_end)

        print
        print 'Schedule:', schedule.get_schedule_item_as_string(schedule_item)

        output_file_name = os.path.join(output_dir, make_output_file_name(date, schedule_item, 'wav'))
        print 'Output file:', os.path.split(output_file_name)[1]

        wav_writer = wave.open(output_file_name, 'wb')
        wav_writer.setparams(output_wav_params)
        for wav_file_start, wav_file_end, wav_file_path in bounds_and_files:
            if wav_file_start.date() != date \
            or wav_file_end.date() != date \
            or wav_file_end <= actual_time_start \
            or wav_file_start >= actual_time_end:
                continue

            wav_reader = wave.open(wav_file_path, 'rb')
            start_frame = end_frame = None
            if wav_file_start < actual_time_start:
                start_frame = (actual_time_start - wav_file_start).seconds * frame_rate
            if wav_file_end > actual_time_end:
                end_frame = (actual_time_end - wav_file_start).seconds * frame_rate
            if start_frame is None:
                start_frame = 0
            if end_frame is None:
                end_frame = wav_reader.getnframes()

            to_read = start_frame
            print 'Skipping', utils.format_large_number(to_read), 'frames in', os.path.split(wav_file_path)[1]
            while to_read > 0:
                data = wav_reader.readframes(min(to_read, frame_chunk))
                if not data:
                    break
                to_read -= (len(data) / frame_size)

            to_read = end_frame - start_frame
            print 'Copying', utils.format_large_number(to_read), 'frames from', os.path.split(wav_file_path)[1]
            while to_read > 0:
                data = wav_reader.readframes(min(to_read, frame_chunk))
                if not data:
                    break
                to_read -= (len(data) / frame_size)
                wav_writer.writeframes(data)
            wav_reader.close()

        wrote_frames = wav_writer.getnframes()
        wav_writer.close()
        if wrote_frames:
            print 'Wrote', utils.format_large_number(wrote_frames), 'frames'
        else:
            print 'Wrote no frames; deleting empty file'
            os.unlink(output_file_name)

        output_wav_files.append(output_file_name)

    return output_wav_files


def make_output_file_name(date, schedule_item, ext, extra=None):
    time_start, time_end, pad_start, pad_end, show, presenters = schedule_item
    base_items = [
        date.strftime('%Y%m%d'),
        time_start.strftime('%H%M%S'),
        time_end.strftime('%H%M%S'),
        ','.join([show] + (presenters or [])),
    ]
    if extra:
        base_items.append(extra)
    fname = '_'.join(base_items)
    if ext:
        fname += '.' + ext
    return fname


# XXX Print some things here to say we're doing things...
def encode_file(path, details=None):
    from rsab.listenagain import config, ListenAgainConfigError
    import schedule
    import utils

    import os

    if details is None:
        details = schedule.schedule_from_audio_file_name(path)
    if details is None:
        print 'No details available from path name; skipping:', os.path.split(path)[1]
        return None

    # Get items from encoder section.  Find any called "command".
    commands = []
    if config.has_section('encoder'):
        for key, value in config.items('encoder', raw=True):
            if key == 'command' or key.startswith('command.'):
                if key == 'command':
                    after_first = False
                    n = 0
                else:
                    after_first = True
                    try:
                        n = int(key.split('.')[1])
                    except ValueError:
                        raise ListenAgainConfigError('[encoder] command not of form "command.N"', key)
                commands.append( (after_first, n, value) )

    commands.sort()
    if not commands:
        raise ListenAgainConfigError('No encoding commands defined')

    def escape(s):
        return s.replace('"', '\\"')

    if config.has_option('main', 'mp3s'):
        output_dir = config.get('main', 'mp3s')
    else:
        output_dir = os.getcwd()
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print 'Encoding', os.path.split(path)[1]

    if config.has_option('encoder', 'artist'):
        artist = config.get('encoder', 'artist')
    else:
        artist = 'Radio St Austell Bay'
    # XXX Need to map internal show code to a real name
    show_date = details['date'].strftime('%d %B %Y')
    show_name = '%s, %s' % (details['show'], show_date)

    input_file_name = path
    output_file_name = os.path.splitext(os.path.split(path)[1])[0] + '.mp3'
    option_vars = {
        'artist': escape(artist),
        'title': escape(show_name),
        'year': escape(str(details['date'].year)),
        'input': escape(input_file_name),
        'output': escape(os.path.join(output_dir, output_file_name)),
    }
    if config.has_option('encoder', 'image'):
        option_vars['image'] = config.get('encoder', 'image')

    for dummy, dummy, command in commands:
        print '  -> ', command % option_vars
        pipe = os.popen(command % option_vars)
        exit_status = pipe.close()
        # All commands after the first must operate on the output from the
        # first command.
        option_vars['input'] = option_vars['output']

    print 'file done.'

    return output_file_name

