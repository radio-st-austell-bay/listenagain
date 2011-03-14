    # XXX There's a dearth of error-handling here.  There MUST be more.

from ftplib import FTP as _FTP

TOTAL_FAILURES_MULTIPLIER = 5
BACKOFF_TIMES = {
    1: 5,
    2: 10,
    3: 30,
    4: 90,
    None: 300, # any number not listed
}

DEBUG_CONNECTION = 0

# This pattern is intended to match the size and file name columns in output
# such as this (which starts with no whitespace):
# -rw-r--r--    1 larsab     larsab          63655 Mar 14 21:36 index.html
DIR_PATTERN = '^[^ ]+ +[0-9]+ +[^ ]+ +[^ ]+ +([0-9]+) +[a-zA-Z]+ +[0-9]+ +[0-9]+:[0-9]+ +(.*)'

class ListenAgainFTP(_FTP):

    def __init__(self, *args, **kwargs):
        _FTP.__init__(self, *args, **kwargs)
        self._laftp_config = {}
        from rsab.listenagain import config, ListenAgainConfigError
        SECTION_NAME = 'ftp'
        for config_key, key in [
            ('audio_path', 'audio_path'),
        ]:
            if not config.has_option(SECTION_NAME, config_key):
                raise ListenAgainConfigError('Missing option', SECTION_NAME, config_key)
            self._laftp_config[key] = config.get(SECTION_NAME, config_key)


    def exists(self, path):
        import os.path
        head, tail = os.path.split(path)
        return tail in self.nlst(head)


    def get_size(self, path):
        import re
        pattern = re.compile(DIR_PATTERN)
        intermediate_namespace = { 'size': None }
        def callback(line):
            match = pattern.match(line)
            if match is None:
                return
            size, fname = match.groups()
            if fname != path:
                return
            try:
                size = int(size)
            except ValueError:
                size = None
            intermediate_namespace['size'] = size
        self.dir(path, callback)
        return intermediate_namespace['size']


    def make_dir(self, dirpath):
        dirpath = dirpath.replace('\\', '/').split('/')
        pwd = self.pwd()
        if dirpath and not dirpath[0]:
            self.cwd('/')
            del dirpath[0]
        for d in dirpath:
            if d not in self.nlst():
                self.mkd(d)
            self.cwd(d)
        self.cwd(pwd)
        return


    def cwd_make_if(self, dirpath):
        self.make_dir(dirpath)
        self.cwd(dirpath)


    def remove_old_audio(self, earliest_keep_date, quiet=False):
        if not self.exists(self._laftp_config['audio_path']):
            return

        import datetime
        import schedule
        pwd = self.pwd()
        self.cwd(self._laftp_config['audio_path'])
        remote_list = self.nlst()
        deleted = []
        for fname in remote_list:
            if fname.startswith('.'):
                continue
            schedule_data = schedule.schedule_from_audio_file_name(fname)
            if schedule_data is not None \
            and schedule_data['date'] < earliest_keep_date:
                if not quiet:
                    print 'Deleting remote file:', fname, '...',
                self.delete(fname)
                if not quiet:
                    print 'done.'
                deleted.append(fname)
        self.cwd(pwd)
        return deleted


    def get_list_of_audio_files(self):
        return [
            fname
            for fname in self.nlst(self._laftp_config['audio_path'])
            if not fname.startswith('.')
        ]


    def upload_index(self, index):
        raise NotImplementedError


_connection = None
def connect(reconnect=False):
    global _connection
    if _connection is None or reconnect:
        from rsab.listenagain import config, ListenAgainConfigError
        for key in ['domain', 'port', 'username', 'password']:
            if not config.has_option('ftp', key):
                raise ListenAgainConfigError('Missing config value', 'ftp', key)

        domain = config.get('ftp', 'domain')
        port = config.get('ftp', 'port')
        if port:
            try:
                port = int(port)
            except ValueError:
                raise ListenAgainConfigError('FTP port not an integer', port)
        else:
            port = 0

        import socket
        socket_default_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(20)
        _connection = ListenAgainFTP()
        _connection.connect(domain, port)
        _connection.login(config.get('ftp', 'username'), config.get('ftp', 'password'))
        socket.setdefaulttimeout(socket_default_timeout)
        if DEBUG_CONNECTION:
            _connection.set_debuglevel(DEBUG_CONNECTION)

    return _connection


def disconnect():
    global _connection
    if _connection is not None:
        import ftplib
        try:
            _connection.quit()
        except ftplib.all_errors:
            pass
    _connection = None
    return _connection


def upload_audio(conn, audio_files, quiet=False):
    import ftplib
    import os
    import stat
    import time

    pwd = conn.pwd()
    conn.cwd_make_if(conn._laftp_config['audio_path'])
    ALLOWED_FAILURES = TOTAL_FAILURES_MULTIPLIER * len(audio_files)
    total_failures = 0
    failures = 0
    must_reconnect = False
    stored = []
    audio_files = audio_files[:]
    while audio_files:
        fpath = audio_files[0]
        del audio_files[0]
        fname = os.path.split(fpath)[1]

        if must_reconnect:
            conn = connect(reconnect=True)
            conn.cwd(conn._laftp_config['audio_path'])
            must_reconnect = False

        local_size = os.stat(fpath)[stat.ST_SIZE]
        remote_size = conn.get_size(fname)
        if remote_size is None:
            if not quiet:
                print 'File not present remotely: %s' % (fname,)
        elif remote_size != local_size:
            if not quiet:
                print 'Remote file size mismatch (local: %s, remote: %s): %s' % (
                    local_size, remote_size, fname,
                )
        else:
            if not quiet:
                print 'Already uploaded: %s' % (fname,)
            continue
        f = open(fpath, 'rb')
        if not quiet:
            print 'Uploading...',
        try:
            conn.storbinary('STOR %s' % (fname,), f)
        except ftplib.all_errors, e:
            f.close()
            audio_files.insert(0, fpath)
            must_reconnect = True
            if not quiet:
                print 'failed:', str(e)
            failures += 1
            total_failures += 1
            if total_failures > ALLOWED_FAILURES:
                print 'Too many failures (%d).  Aborting audio upload.' % (total_failures,)
                conn = disconnect()
                break
            print 'Failures: %d (total: %d)' % (failures, total_failures)
            wait_for = BACKOFF_TIMES.get(failures, BACKOFF_TIMES[None])
            print 'Waiting for', wait_for, 'seconds before retrying...',
            time.sleep(wait_for)
            print 'done.'
        else:
            f.close()
            if not quiet:
                print 'done.'
            failures = 0
        stored.append(fname)
    if conn is not None:
        conn.cwd(pwd)

    return stored

