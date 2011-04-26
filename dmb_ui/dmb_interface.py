# -*- coding: utf-8 -*-

import sys, dmb_xmpp, config
from dmb_main.commands import *
from dmb_main.kernel import *
import dmb_main.kernel
from dmb_main.service import dmb_service
from dmb_main.dmb_log import log
import threading, Queue, time

queue_input = Queue.Queue(0)
queue_output = Queue.Queue(0)
is_run = 1

class inputThread(threading.Thread):

	def __init__(self, ui):
		threading.Thread.__init__(self)
		self.ui = ui		
		self.dmb = dmb_service()

	def run(self):
		global is_run
		while is_run:
			try:
				jid, message, login = queue_input.get(timeout = 10)
				log.debug('%s %s' % (jid, message))
				if not login:
					try:
						login = self.dmb.getLogin(jid = jid)
					except dmbErrorAuth:
						login = 'anonymous'
				try:
					self.dmb.def_locale = self.dmb.getUserParams(login)['locale']
				except:
					log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))			
					self.dmb.def_locale = 'en'
				try:
					if jid == config.admin:
						mesg = adminParsing(self.dmb, login = unicode(login), text = unicode(message), jid = jid)
					else:
						mesg = parsing(self.dmb, login = unicode(login), text = unicode(message), jid = jid)
				except SystemExit:
					log.info('exit')
					is_run = None
					self.ui.is_run = None
					sys.exit()
				except dmbError as exc:
					log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))			
					mesg = '%s %s' % (exc.getText(), self.dmb.getText(exc.getCode()))
				except:
					log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
					mesg = self.dmb.getText('ERR7')
				if jid in kernel.dmb_servers:
					extra = {'dmb': 'server', 'dmb_type': 'send', 'dmb_login': login.split('@')[0]}
				else:
					extra = {}
				queue_output.put((jid, mesg, extra))
				self.queueHandle()
			except Queue.Empty:
				pass

	def queueHandle(self):
		if self.dmb.queue_to_send:
			for rec in self.dmb.queue_to_send:
				sended = 0
				for j in rec['jid']:
					if rec.get('send') or self.ui.getStatus(j):
						queue_output.put((j, rec.get('message'), rec.get('extra')))
						sended = 1
						break
				if not sended:
					post = rec.get('post')
					message = rec.get('message')
					comment = rec.get('comment')
					id_recommend = rec.get('id_recommend')
					try:
						self.dmb.addToSendQueue(login = rec['login'], post = post, comment = comment, id_recommend = id_recommend, message = message)
					except dmbError:
						log.debug('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
					except:
						log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
			self.dmb.queue_to_send = []

class outputThread(threading.Thread):

	def __init__(self, ui):
		threading.Thread.__init__(self)
		self.ui = ui		

	def run(self):
		global is_run
		while is_run:
			try:
				jid, mesg, extra = queue_output.get(timeout = 10)
				self.ui.send(jid, mesg, extra)
			except Queue.Empty:
				pass

class dmb_interface:

	def getActiveJid(self, jids):
		for j in jids:
			if self.xmpp_client.getStatus(j):
				return j
		return jids[0]

	def __init__(self):
		self.xmpp_client = dmb_xmpp.dmb_bot_client(config.bot_jid, config.bot_passwd, messageFunc = self.commandHandler, presenceFunc = self.presenceHandler, s2sFunc = self.s2sHandler)
		self.dmb = dmb_service()
		kernel.dmb_servers = self.dmb.getServers()
		log.debug(str(kernel.dmb_servers))
		self.threads = []
		for i in xrange(config.threads_count):
			self.threads.append(inputThread(self.xmpp_client))
			self.threads[-1].start()
		self.threads.append(outputThread(self.xmpp_client))
		self.threads[-1].start()

	def presenceHandler(self, jid, state):
		try:
			login = self.dmb.getLogin(jid)
			queue = self.dmb.getSendQueue(login)
			message = ''
			for q in queue:
				message += q
			queue_output.put((jid, message, {}))
			self.dmb.delFromSendQueue(login)
		except dmbError as exc:
			log.debug('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))

	def commandHandler(self, jid, message):
		queue_input.put((jid, message, None))

	def s2sHandler(self, jid, type_msg, message, login = None):
		log.debug('***s2s*** %s %s' % (jid, message))
		if type_msg == 'reg':
			if jid in kernel.dmb_servers:
				queue_output.put((jid, 'empty', {'dmb_type': 'ok'}))
			else:
				if config.s2s_reg == s2s_reg_deny:
					queue_output.put((jid, 'empty', {'dmb_type': 'deny'}))
				elif config.s2s_reg == s2s_reg_allow_confirm:
					queue_output.put((config.admin, '%s want to register' % jid, {}))
				else:
					try:
						kernel.dmb_servers = self.dmb.addServer(jid)
					except dmbErrorRepeat:
						pass
					else:
						queue_output.put((config.admin, 'server %s registry' % jid, {}))
				queue_output.put((jid, 'empty', {'dmb': 'server', 'dmb_type': 'ok'}))
		elif config.s2s_msg == s2s_msg_allow:
			if type_msg == 'send':
				queue_output.put((self.getActiveJid(self.dmb.getJid(login)), message, {}))
			elif type_msg == 'command':
				queue_input.put((jid, message, '%s@%s' % (login, getServerName(jid))))

	def xmpp_start(self):
		self.xmpp_client.process()
		self.xmpp_client.close()
