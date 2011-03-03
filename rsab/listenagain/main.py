
# Next:
# - Wrap all this in try/except and try/finally with logging
# - Add auto subversion version number to pass to optionparser:
#   http://stackoverflow.com/questions/4351032/automatic-version-numbering
# - add tee class
# - add function to make log file (named after date, with (2) if nec.)
# - be more verbose
# - email log
# - encode new WAV files
# - option to time construction of a WAV file of N seconds (for tuning frame
#   chunk size config value).
# - options to do some things but not others:
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
# - make RSS feeds when we make the index.
# - error-handling for FTP: what if we can't get access to the server?  What if
#   we have it but lose it?  (We need to make an index file which covers the
#   files we won't delete but none of the new ones, upload that, then delete
#   the old ones and upload the new ones before finally uploading the new
#   index.)
# - more FTP: check for existing file before uploading.  If it's the same size,
#   don't upload.  If it's smaller, resume if possible rather than uploading.
#   If we lose the connection, sleep and retry up to some limit -- last night
#   it seems there was a blip in the connection.
# - Web server: need it to support ranges.
# - jPlayer: need a wider seek bar?
# - Can we supply a time to jPlayer so it doesn't have to download file right
#   now in order to display duration?
# - 'ended' event doesn't seem to be firing...
# - use jQuery to make table prettier, sortable, filterable.
# - add disclaimer to page about these files not being edited, and contact
#   address for complaints or whatever.
# - Use jPlayer 'play' event to highlight row, not click handler of row. ?
# - upload items from www directory.
# - Live:
#   - Add extra field to schedule: "record".  If 0, we don't record.
#   - Parse schedule for next day and generate records to use for Live.  Every
#     minute or so, update text in playlist (and in now playing if required) if
#     the schedule indicates the program has changed.  Update filtering too.
#   - Have text for Record Spinning Auto Bot for when there's no show on.
# - Separation:
#   - Use ajax to retrieve table content.
# - Cosmetic:
#   - Disclaimer
#   - Having trouble? dialog with HTML5/Flash text and link to M3U.
# - FTP:
#   - Delete MP3 after uploading.
#   - New FTP method to check existence and correct size.
#   - MP3 upload method: return success if file already there and of correct
#     size (so it can be deleted).  Return success if upload succeeds.  Trap
#     errors and return failure.
#   - Maintain dict mapping consecutive failures to seconds of wait (and None
#     key for anything above highest explicit int key).  Each time an FTP
#     method fails, increment the failures counter and wait appropriately.  If
#     a method succeeds, reset the consecutive failures counter (but keep the
#     total failures counter, which we'll test against a max allowed failures
#     number, which will be relative to the number of files).  We may want to
#     wrap this logic up in a wrapper method which the FTP class applies to all
#     server-connecting methods.  Or to just those which are uploading?  Put
#     try/except in wrapper around all methods, but only increment total
#     counter for uploads?


def run():
    from optparse import OptionParser
    import datetime
    import glob
    import os
    import time

    import audio
    import html
    import utils
    import recorder
    import remote
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
        options.index = True
        options.upload = True

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
        if True: # XXX look for no-delete option later
            print 'Deleting local copies of WAVs...'
            for (wav, mp3) in zip(wav_files, mp3_files):
                if mp3 is not None and os.path.isfile(wav):
                    os.unlink(wav)
                    print '   ', wav
            print 'done.'
            print

    ftp_conn = None
    remote_audio_files = []
    if options.upload or options.index:
        if config.has_option('ftp', 'keep_days'):
            keep_days = config.getint('ftp', 'keep_days')
        else:
            keep_days = 7
        earliest_keep_date = date - datetime.timedelta(days=keep_days-1)
        ftp_conn = remote.connect()
        remote_audio_files = ftp_conn.get_list_of_audio_files()

        # First make an index with no old files:
        audio_files_for_first_index = [
            fname
            for (fname, details) in [
                (fname, schedule.schedule_from_audio_file_name(fname))
                for fname in remote_audio_files
            ]
            if details is not None and details['date'] >= earliest_keep_date
        ]

        index_fname = html.make_index_file(audio_files_for_first_index)
        if options.upload:
            ftp_conn.storlines('STOR index.html', open(index_fname, 'r'))

    if options.upload:
        ftp_conn.remove_old_audio(earliest_keep_date)

        if mp3_files is None:
            if config.has_option('main', 'mp3s'):
                mp3s_dir = config.get('main', 'mp3s')
            else:
                mp3s_dir = os.getcwd()
            mp3_files = glob.glob(os.path.join(mp3s_dir, '*.mp3'))
        uploaded = ftp_conn.upload_audio(mp3_files)

        if True: # XXX look for no-delete option later
            print 'Deleting local copies of MP3s...'
            for mp3_path in mp3_files:
                if os.path.split(mp3_path)[1] in uploaded \
                and os.path.isfile(mp3_path):
                    print '   ', mp3_path
                    os.unlink(mp3_path)
            print 'done.'
            print

    if options.index:
        # Second index file: whatever's on the server.
        remote_audio_files = ftp_conn.get_list_of_audio_files()
        index_fname = html.make_index_file(remote_audio_files)
        if options.upload:
            ftp_conn.storlines('STOR index.html', open(index_fname, 'r'))
            # XXX Now also sync up anything that's in the www directory
            # (resource files such as JS, CSS, images, jPlayer...).
            pass

    if ftp_conn is not None:
        ftp_conn.quit()

    end_time = time.time()
    if not options.print_only:
        duration = end_time - start_time
        print 'Took %2.2dm %2.2ds' % divmod(duration, 60)


    return 0


if __name__ == '__main__':
    run()

