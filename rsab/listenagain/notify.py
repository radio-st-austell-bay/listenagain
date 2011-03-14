
DEFAULT_FROM = 'listenagain@rsab.org'

def _send(message_list):
    from rsab.listenagain import config

    import email.Utils
    import smtplib

    if config.has_option('email', 'from'):
        email_from = config.get('email', 'from')
    else:
        email_from = DEFAULT_FROM

    if config.has_option('email', 'smtphost'):
        smtphost = config.get('email', 'smtphost')
    else:
        smtphost = ''
    if not smtphost:
        raise ListenAgainConfigError('[email]/smtphost not set')

    if config.has_option('email', 'smtpport'):
        smtpport = config.getint('email', 'smtpport')
    else:
        smtpport = None
    if not smtpport:
        smtpport = 25

    if config.has_option('email', 'smtpusername'):
        smtpusername = config.get('email', 'smtpusername')
    else:
        smtpusername = ''
    if config.has_option('email', 'smtppassword'):
        smtppassword = config.get('email', 'smtppassword')
    else:
        smtppassword = ''

    sent = 0
    smtp = smtplib.SMTP(smtphost, smtpport)
    if smtpusername:
        try:
            smtp.login(smtpusername, smtppassword)
        except smtplib.SMTPException, e:
            print 'ERROR: Could not log in to SMTP server.'
            print e
            return sent

    for message in message_list:
        to_list = [tpl[1] for tpl in email.Utils.getaddresses(message.get_all('to', []))]
        print 'Sending message to:', ', '.join(to_list),
        try:
            smtp.sendmail(email_from, to_list, message.as_string())
        except smtplib.SMTPException, e:
            print
            print 'ERROR: Could not send message.'
            print e
        else:
            print 'sent.'
            sent += 1

    return sent


def notify_all(uploaded_files):
    from rsab.listenagain import config
    import html
    import schedule

    from email.MIMEText import MIMEText
    import os
    import sets

    if uploaded_files is None:
        return

    mapping = { None: sets.Set(uploaded_files), }
    for fname in uploaded_files:
        details = schedule.schedule_from_audio_file_name(fname)
        for name in [details['show']] + details.get('presenters', []):
            if name not in mapping:
                mapping[name] = sets.Set()
            mapping[name].add(fname)

    config_sections = [
        sname
        for sname in config.sections()
        if sname == 'notify' or sname.startswith('notify.')
    ]

    if config.has_option('ftp', 'keep_days'):
        keep_days = config.getint('ftp', 'keep_days')
    else:
        keep_days = 7
    if config.has_option('main', 'userfacingserveraddress'):
        remote_server = config.get('main', 'userfacingserveraddress')
    else:
        remote_server = 'http://listenagain.rsab.org'
    if config.has_option('ftp', 'audio_path'):
        remote_path = config.get('ftp', 'audio_path')
    else:
        remote_path = '/audio'
    if config.has_option('email', 'from'):
        email_from = config.get('email', 'from')
    else:
        email_from = DEFAULT_FROM


    print
    print 'Notification emails:'

    messages = []
    for section in config_sections:
        print
        print 'Section name:', section
        if config.has_option(section, 'email'):
            addresses = filter(None, [x.strip() for x in config.get(section, 'email').split(',')])
        else:
            addresses = []
        print 'Addresses:', (addresses and ', '.join(addresses) or '(none)')
        if not addresses:
            print 'Skipping'
            continue

        if config.has_option(section, 'match'):
            match_names = filter(None, [x.strip() for x in config.get(section, 'match').split(',')])
        else:
            match_names = []
        print 'Requested:', ('*' in match_names and '(all)' or ', '.join(match_names))

        if '*' in match_names:
            notify_files = list(mapping[None])
        elif match_names:
            notify_files = sets.Set()
            for name in match_names:
                notify_files.update(mapping.get(name, []))
            notify_files = list(notify_files)
        else:
            notify_files = []

        if not notify_files:
            print 'No files matched.'
            continue

        notify_files.sort()

        if config.has_option(section, 'subject'):
            subject = config.get(section, 'subject')
        else:
            subject = 'New files uploaded by Radio St Austell Bay'

        if config.has_option(section, 'template'):
            template_name = config.get(section, 'template')
        else:
            template_name = 'mail-notify-default.txt'

        template = html.Template(template_name) # Not actually HTML!

        template.keep_days = keep_days
        files_string = '\n'.join([
            '    %s%s/%s' % (
                remote_server,
                remote_path,
                os.path.split(fname)[1],
            )
            for fname in notify_files
        ])
        template.files = files_string
        print 'Files:'
        print files_string

        message = MIMEText(str(template))
        message['Subject'] = subject
        message['From'] = email_from
        message['To'] = ', '.join(addresses)
        messages.append(message)

    print
    print 'Sending messages...'
    print
    sent = _send(messages)
    print
    print 'Done.  Sent %s of %s messages' % (sent, len(messages))
