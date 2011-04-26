# -*- coding: utf-8 -*-

import logging, logging.handlers
import config

log = logging.getLogger('service')
log.setLevel(config.log['level'])
hand = logging.handlers.RotatingFileHandler(config.log['filename'], maxBytes=config.log['maxBytes'], backupCount=config.log['backupCount'])
hand.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(module)s(%(funcName)s) %(message)s"))
log.addHandler(hand)
