
# Next:
# - Wrap all this in try/except and try/finally with logging
# - Add auto subversion version number to pass to optionparser
# - add tee class
# - add function to make log file (named after date, with (2) if nec.)
# - be more verbose
# - implement schedule printer (always print it, and sometimes do no more)
# - email log
# - Utility to parse WAV/MP3 name to get start/end/show/presenters.
# - encode new WAV files
# - option to time construction of a WAV file of N seconds (for tuning frame
#   chunk size config value).
# - options to do some things but not others:
#   -w: make WAV files
#   -m: make MP3 files (using WAVs from -w run)
#   -i: make index pages (using all MP3s found)
#   -u: upload MP3s and index files, and delete old MP3s from server
# - option to not delete working files
# - allow multiple arguments for multiple dates.  Wrap up the relevant bits of
#   this function in a loop.
# - change schedule items to be instances of Schedule class, which will have
#   start/end attributes (datetimes; no need to keep them as just times), pad
#   attributes (not dynamic as we must distinguish between cases where we've
#   read the schedule file and parsed file names), show and presenter names and
#   methods for translating them.
# - fname parser to use regexes and be in schedule module.
# - write a class to write a progress bar to stdout for when making WAVs.


def run():
    from optparse import OptionParser
    import glob
    import os
    import time

    import audio
    import utils
    import recorder
    import schedule

    option_parser = OptionParser()
    option_parser.add_option(
        '-p',
        '--print',
        dest='print_only',
        action='store_true',
        default=False,
        help="Print information about the date but don't do anything",
    )

    option_parser.add_option(
        '-w',
        '--wav',
        dest='wavs',
        action='store_true',
        default=False,
        help="Construct WAVs",
    )

    option_parser.add_option(
        '-e',
        '--encode',
        dest='encode',
        action='store_true',
        default=False,
        help="Encode MP3s",
    )

    option_parser.add_option(
        '-i',
        '--index',
        dest='index',
        action='store_true',
        default=False,
        help="Generate index pages",
    )

    option_parser.add_option(
        '-u',
        '--upload',
        dest='upload',
        action='store_true',
        default=False,
        help="Upload data to web server",
    )

    option_parser.add_option(
        '-c',
        '--config',
        dest='config_file',
        help="Specify alternative config file",
        metavar='FILE',
    )

    options, args = option_parser.parse_args()

    # Print only: do nothing else.
    if options.print_only:
        options.wavs = options.encode = options.index = options.upload = False

    # No specific do-something options were given.  Do everything.
    elif not options.wavs and not options.encode and not options.index and not options.upload:
        options.wavs = True
        options.encode = True
        options.index = False#True
        options.upload = False#True

    config_files = utils.default_config_files()
    if options.config_file is not None:
        config_files.append(options.config_file)
    config = utils.init_config(config_files)

    date_string = 'yesterday'
    if len(args) == 1:
        date_string = args[0]
    date = utils.interpret_date_string(date_string)

    start_time = time.time()

    recorder.init_module()
    bounds_and_files = recorder.get_bounds_and_files_for_date(date)
    schedule_list = schedule.get_schedule(date)

    if options.wavs or options.print_only:
        print 'Schedule:'
        schedule.print_schedule(schedule_list)
        print
        print 'Recordings:'
        recorder.print_bounds_and_files(bounds_and_files)

    wav_files = None
    if options.wavs:
        wav_files = audio.make_wav_files(date, bounds_and_files, schedule_list)

    mp3_files = None
    if options.encode:
        if wav_files is None:
            if config.has_option('main', 'wavs'):
                wavs_dir = config.get('main', 'wavs')
            else:
                wavs_dir = os.getcwd()
            wav_files = glob.glob(os.path.join(wavs_dir, '*.wav'))
        # XXX Delete working WAVs?  Only if MP3 was created for it.
        mp3_files = [
            audio.encode_file(path)
            for path in wav_files
        ]
        for (wav, mp3) in zip(wav_files, mp3_files):
            if mp3 is not None:
                pass # Delete WAV if no-delete option isn't present

    if options.upload:
        if mp3_files is None:
            raise NotImplementedError('get list of MP3 files')
        raise NotImplementedError('upload MP3s and delete old ones')

    if options.upload or options.index:
        raise NotImplementedError('connect to server to get list of files')
        if not options.upload:
            # XXX Modify list based on current recordings, or make index for
            # what's been uploaded already?
            raise NotImplementedError

    if options.index:
        raise NotImplementedError('Build index files')
        if options.upload:
            raise NotImplementedError('Upload index files')

    end_time = time.time()
    if not options.print_only:
        duration = end_time - start_time
        print 'Took %2.2dm %2.2ds' % divmod(duration, 60)


    return 0


if __name__ == '__main__':
    run()
