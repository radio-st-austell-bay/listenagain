# XXX There's a dearth of error-handling here.  There MUST be more.

from ftplib import FTP as _FTP

class ListenAgainFTP(_FTP):

    def __init__(self, *args, **kwargs):
        _FTP.__init__(self, *args, **kwargs)
        self._laftp_config = {}
        from rsab.listenagain import config, ListenAgainConfigError
        SECTION_NAME = 'ftp'
        for config_key, key in [
            ('audio_path', 'audio_path'),
            ('date_index', 'index_by_date'),
            ('presenter_index', 'index_by_presenter'),
        ]:
            if not config.has_option(SECTION_NAME, config_key):
                raise ListenAgainConfigError('Missing option', SECTION_NAME, config_key)
            self._laftp_config[key] = config.get(SECTION_NAME, config_key)


    def exists(self, path):
        import os.path
        head, tail = os.path.split(path)
        return tail in self.nlst(head)


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


    def upload_audio(self, audio_files, quiet=False):
        import os.path
        pwd = self.pwd()
        self.cwd_make_if(self._laftp_config['audio_path'])
        stored = []
        for fpath in audio_files:
            fname = os.path.split(fpath)[1]
            f = open(fpath, 'rb')
            if not quiet:
                print 'Uploading file:', fname, '...',
            self.storbinary('STOR %s' % (fname,), f)
            if not quiet:
                print 'done.'
            stored.append(fname)
        self.cwd(pwd)
        return stored


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
            if schedule_data['date'] < earliest_keep_date:
                if not quiet:
                    print 'Deleting remote file:', fname, '...',
                self.delete(fname)
                if not quiet:
                    print 'done.'
                deleted.append(fname)
        return deleted


    def get_list_of_audio_files(self):
        return [
            fname
            for fname in self.nlst(self._laftp_config['audio_path'])
            if not fname.startswith('.')
        ]


    def upload_index(self, index):
        raise NotImplementedError


def connect():
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

    conn = ListenAgainFTP()
    conn.connect(domain, port)
    conn.login(config.get('ftp', 'username'), config.get('ftp', 'password'))
    return conn


def disconnect(conn):
    conn.quit()

