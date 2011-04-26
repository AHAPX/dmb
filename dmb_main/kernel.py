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

class dmbError(Exception):

	def __init__(self, code = 'ERR7'):
		self.code = code
		self.message = ''
	def getCode(self):
		return self.code
	def getText(self):
		return self.message

class dmbErrorAuth(dmbError):
	def __init__(self, code = 'ERR1'):
		dmbError.__init__(self, code)

class dmbErrorEmpty(dmbError):
	def __init__(self, code = 'ERR2'):
		dmbError.__init__(self, code)

class dmbErrorNotFound(dmbError):
	def __init__(self, code = 'ERR4'):
		dmbError.__init__(self, code)

class dmbErrorRepeat(dmbError):
	def __init__(self, code = 'ERR5'):
		dmbError.__init__(self, code)

class dmbErrorAccess(dmbError):
	def __init__(self, code = 'ERR6'):
		dmbError.__init__(self, code)

class dmbErrorUnknown(dmbError):
	def __init__(self, code = 'ERR7'):
		dmbError.__init__(self, code)

class dmbErrorParsing(dmbError):
	def __init__(self, code = 'ERR8'):
		dmbError.__init__(self, code)

class dmbErrorBusy(dmbError):
	def __init__(self, code = 'ERR9'):
		dmbError.__init__(self, code)

class dmbErrorCommand(dmbError):
	def __init__(self, code = 'ERR11'):
		dmbError.__init__(self, code)

class dmbErrorSyntax(dmbError):
	def __init__(self, code = 'ERR12'):
		dmbError.__init__(self, code)
