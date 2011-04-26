const_post = 1
const_comment = 2
const_user = 3

access_allow_all = 10
access_deny_black = 20
access_allow_white = 30
access_deny_all = 40

s2s_reg_deny = 1
s2s_reg_allow_confirm = 2
s2s_reg_allow = 3

s2s_msg_deny = 1
s2s_msg_allow = 2

dmb_servers = []

def getServerName(jid):
	try:
		bot, srv = jid.split('@', 1)
		if bot == 'dmb':
			return srv
		else:
			return '%s.%s' % (bot, srv)
	except ValueError:
		return jid

def getJidName(server):
	yield 'dmb@%s' % server
	try:
		bot, srv = server.split('.', 1)
		yield '%s@%s' % (bot, srv)
	except ValueError:
		raise dmbErrorNotFound

class dmbError(Exception):

	def __init__(self, code = 'ERR7', message = ''):
		self.code = code
		self.message = message

	def getCode(self):
		return self.code

	def getText(self):
		return self.message

class dmbErrorAuth(dmbError):
	def __init__(self, code = 'ERR1', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorEmpty(dmbError):
	def __init__(self, code = 'ERR2', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorNotFound(dmbError):
	def __init__(self, code = 'ERR4', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorRepeat(dmbError):
	def __init__(self, code = 'ERR5', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorAccess(dmbError):
	def __init__(self, code = 'ERR6', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorUnknown(dmbError):
	def __init__(self, code = 'ERR7', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorParsing(dmbError):
	def __init__(self, code = 'ERR8', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorBusy(dmbError):
	def __init__(self, code = 'ERR9', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorCommand(dmbError):
	def __init__(self, code = 'ERR11', message = ''):
		dmbError.__init__(self, code, message)

class dmbErrorSyntax(dmbError):
	def __init__(self, code = 'ERR12', message = ''):
		dmbError.__init__(self, code, message)
