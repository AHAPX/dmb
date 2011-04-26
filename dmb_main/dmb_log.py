# -*- coding: utf-8 -*-

import logging, logging.handlers
import config

log = logging.getLogger('service')
log.setLevel(config.log['level'])
hand = logging.handlers.RotatingFileHandler(config.log['filename'], maxBytes=config.log['maxBytes'], backupCount=config.log['backupCount'])
hand.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(module)s(%(funcName)s) %(message)s"))
log.addHandler(hand)

log_cntr = logging.getLogger('counters')
log_cntr.setLevel(config.log_counters['level'])
hand = logging.handlers.RotatingFileHandler(config.log_counters['filename'], maxBytes=config.log_counters['maxBytes'], backupCount=config.log_counters['backupCount'])
hand.setFormatter(logging.Formatter("%(asctime)s %(levelname)s - %(message)s"))
log_cntr.addHandler(hand)
