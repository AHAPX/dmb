# -*- coding: utf-8 -*- 

from dmb_ui.dmb_xmpp import *

client = dmb_bot_client('anarchy@jabber.cc', 'warishell')
client.process()
client.close()
