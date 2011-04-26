# -*- coding: utf8 -*-

import logging

admin = 'anapx@jabber.ru'
bot_jid = 'dmb_bot@jabber.ru'
bot_passwd = 'password'

db_host = 'localhost'
db_port = 27017
db_base = 'dmb'
db_user = None
db_pass = None

log = {'filename': '/home/anarchy/logs/dmb', 'level': logging.DEBUG, 'maxBytes': 1048576, 'backupCount': 9}
log_counters = {'filename': '/home/anarchy/logs/counters', 'level': logging.DEBUG, 'maxBytes': 1048576, 'backupCount': 2}

threads_count = 2

s2s_reg = 3
s2s_msg = 2
