import xmpp, time, sys
from dmb_main.dmb_log import log
import config
# -*- coding: utf-8 -*- 

class dmb_bot_client:

	def __init__(self, jid, password, resource = None, messageFunc = None, presenceFunc = None, s2sFunc = None):
		self.messageFunc = messageFunc
		self.presenceFunc = presenceFunc
		self.s2sFunc = s2sFunc
		JID = xmpp.protocol.JID(jid)
		self.client = xmpp.Client(JID.getDomain(), debug = [])
		self.client.connect()
		if self.client.auth(JID.getNode(), password, resource):
			self.client.sendInitPresence()
			self.client.RegisterHandler('message', self.messageHandler)
			self.client.RegisterHandler('presence', self.presenceHandler)
			self.client.send(xmpp.Presence(show = 'chat', priority = 10))
		else:
			print 'Error authification'
			sys.exit(0)
		self.is_run = 1

	def close(self):
		self.client.disconnect()

	def messageHandler(self, conn, msg):
		try:
			log.debug('%s(%s) -> %s' % (msg.getFrom(), msg.getBody(), msg.getAttrs()))
			if msg.getAttrs().get('dmb') == 'server':
				if self.s2sFunc:
					login = msg.getAttrs().get('dmb_login')
					type_msg = msg.getAttrs().get('dmb_type')
					self.s2sFunc(str(msg.getFrom()).split('/')[0], type_msg, msg.getBody(), login)
			elif msg.getBody() and self.messageFunc:
				self.messageFunc(str(msg.getFrom()).split('/')[0], msg.getBody())
		except SystemExit:
			log.info('%s' % 'system exit')
			sys.exit()
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))

	def presenceHandler(self, conn, event):
		try:
			if event:
				log.debug('%s %s' % (event.getFrom(), event.getAttrs()))
				if event.getAttrs().get('type') == 'subscribe':
					self.client.getRoster().Authorize(event.getFrom())
				jid = str(event.getFrom()).split('/')[0]
				status = self.getStatus(jid)
				if status and self.presenceFunc:
					self.presenceFunc(jid, status)
		except SystemExit:
			log.info('%s' % 'system exit')
			sys.exit()
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))

	def getStatus(self, jid):
		try:
			if self.client.getRoster().getItem(jid):
				for res in self.client.getRoster().getItem(jid)['resources'].values():
					if res['show']:
						return res['show']
					else:
						return 'online'
			return None
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))

	def process(self, timeout = 10):
		while self.is_run:
			self.client.Process(timeout)

	def send(self, jid, message, extra):
		try:
			if message:
				message = message.rstrip()
				if message.count('\n'):
					message = '\n' + message
				msg = xmpp.protocol.Message(jid, message, 'chat')
				if extra:
					for k, v in extra.iteritems():
						msg.setAttr(k, v)
				log.debug('%s(%s) -> %s' % (jid, msg.getBody(), msg.getAttrs()))
				self.client.send(msg)
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
