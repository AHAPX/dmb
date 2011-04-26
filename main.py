#!/usr/bin/python
# -*- coding: utf-8 -*- 

#from dmb_db.mongodb import dmb_database
from dmb_main.service import dmb_service
from dmb_ui.dmb_interface import dmb_interface
from dmb_main.kernel import *
import sys
import config

#dmb = dmb_service()
#print dmb.getUserParams('anarchy@dmb.im')
#sys.exit()

interface = dmb_interface()
interface.xmpp_start()
