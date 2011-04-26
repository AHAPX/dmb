# -*- coding: utf-8 -*-

import time, math, sys
from locale import dmb_locale
from dmb_db.mongodb import dmb_database
from kernel import *
from dmb_log import log
import config
from dmb_main.dmb_decorators import timeExecute

class dmb_service:

	code_tables = {'en': 'zabcdefghijklmnopqrstuvwxy', 'ru': u'яабвгдеёжзийклмнопрстуфхцчшэю'}
	queue_to_send = []

	def __init__(self):
		self.locale = dmb_locale('en')
		self.def_locale = 'en'
		self.db = dmb_database(host = config.db_host, port = config.db_port, base = config.db_base, user = config.db_user, passwd = config.db_pass)

	def numCoding(self, x, code_index = 'en'):
		try:
			if not self.code_tables.has_key(code_index):
				return x
			code_table = self.code_tables[code_index]
			result = ''
			while x != None:
				if 9 < x % 100 < len(code_table):
					result += code_table[(x % 100)]
					x /= 100
				else:
					result += code_table[(x % 10)]
					x /= 10
				if x == 0:
					x = None
			return result[::-1]
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))

	def numDecoding(self, s, code_index = 'en'):
		if not self.code_tables.has_key(code_index):
			return s
		code_table = self.code_tables[code_index]
		result = 0
		for c in s:
			try:
				x = code_table.index(c)
				if x > 9:
					result = result * 100 + x
				else:
					result = result * 10 + x
			except:
				return None
		return result

	def normID(self, num):
		if num == '': return num
		if num.isdigit():
			return unicode(num)
		else:
			for key in self.code_tables.keys():
				x = self.numDecoding(num, key)
				if x != None:
					return unicode(x)

	def normilizeID(self, strid):
		try:
			m1 = unicode(strid).split('/')
			result = None
			if len(m1) > 1:
				result = ''
				m2 = unicode(m1[1]).split(',')
				for m in m2:
					if result: result += ','
					m3 = m.split(':')
					if len(m3) > 1:
						result += self.normID(m3[0]) + ':' + self.normID(m3[1])
					else:
						result += self.normID(m3[0])
			return (int(self.normID(m1[0])), result)
		except TypeError:
			log.warning('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
			return None
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
			raise dmbErrorUnknown

	def getText(self, code, locale_name = None):
		if not locale_name:
			locale_name = self.def_locale
		return self.locale.getText(code, locale_name)

	def getStrTime(self, timestamp, main_time = time.time(), suffix = None, time_zone = 0, relativity = 1):
		if not suffix:
			suffix = self.getText('TMS1')
		if relativity:
			dt = int(main_time-timestamp)
			if dt < 2:
				return self.getText('TM1')
			elif dt < 60:
				return '%i %s %s' % (dt, self.getText('TM2'), suffix)
			elif dt < 3600:
				return '%i %s %s' % (dt/60, self.getText('TM3'), suffix)
			elif dt < 86400:
				return '%i %s %s' % (dt/3600, self.getText('TM4'), suffix)
			elif dt < 2592000:
				return '%i %s %s' % (dt/86400, self.getText('TM5'), suffix)
			elif dt < 31104000:
				return '%i %s %s' % (dt/2592000, self.getText('TM6'), suffix)
			elif dt < 311040000:
				return '%i %s %s' % (dt/31104000, self.getText('TM7'), suffix)
		return time.strftime('%d.%m.%Y %H:%M:%S', time.gmtime(timestamp + time_zone*3600))

	@timeExecute(1)
	def addToQueueSend(self, user, post, comment = None, tag = [], id_recommend = None):
		try:
			self.db.addToSendHistory(login = user, post = post, comment = comment)
			subs = self.db.getSubscribers(post = post, user = user, comment = comment, tag = tag)
			if subs:
				old_locale = self.def_locale
				for rec in subs:
					self.def_locale = self.getUserParams(rec)['locale']
					try:
						message = self.getShow(login = rec, post = post, comment = comment, id_recommend = id_recommend, error_mesg = None)
						message = self.show(login = rec, messages = message[0], pre_text = message[1])
					except dmbError as exc:
						log.error(self.getText(exc.getText(), 'en'))
					if message:
						self.queue_to_send.append({'jid': self.getJid(rec), 'message': message, 'login': rec, 'post': post, 'comment': comment, 'id_recommend': id_recommend})
						self.db.addToSendHistory(login = rec, post = post, comment = comment)
				self.def_locale = old_locale
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))			

	def getShow(self, count = 10, login = None, post = None, comment = None, tag = None, user = None, id_recommend = None, error_mesg = 1):
		try:
			if login:
				params = self.getUserParams(login)
				if not params:
					params = self.getUserParams('anonymous')
			else:
				params = self.getUserParams('anonymous')
			if post:
				mess_type = self.getText('ERRMSG1')
				messages = self.db.show(post = post, comment = comment)				
				if comment:
					messages = filter(lambda x: x[0] == const_comment, messages)
			elif user:
				mess_type = self.getText('ERRMSG2')
				messages = self.db.show(user = user)
			elif tag:
				mess_type = self.getText('ERRMSG3')
				messages = self.db.show(count = count, tag = tag, login = login)
			else:
				mess_type = self.getText('ERRMSG1')
				messages = self.db.show(count = count, login = login)
			result = ''
			if id_recommend:
				recommend = self.db.getRecommend(id_recommend)
				if recommend:
					if recommend.has_key('message') and recommend['message']:
						message = '- %s' % recommend['message']
					else:
						message = self.getText('PS1')
					result += '%s %s:\n' % (recommend['login'], message)
			return (messages, result)
		except dmbErrorNotFound as exc:
			log.debug('%s, %s' % (self.getText(exc.getText(), 'en'), mess_type))
			raise type(exc)(message = mess_type)

	@timeExecute(1)
	def show(self, login = None, messages = (), pre_text = ''):
		try:
			time_zone = 0
			if login:
				params = self.getUserParams(login)
				if params:
					time_zone = params['time_zone']
				else:
					params = self.getUserParams('anonymous')
			else:
				params = self.getUserParams('anonymous')
			messages = list(messages)
			short_msg = len(filter(lambda x: x[0] == const_post, messages)) > 1
			result = pre_text
			for message in messages:
				if message[0] == const_post:
					message = message[1]
					tagStr = ''
					for t in message['tags']:
						if not tagStr.count('*%s ' % t):
							tagStr += '*%s ' % t
					if len(tagStr) > 0:
						tagStr += '\n'
					if short_msg and len(message['message']) > 200:
						message['message'] = '%s [...]' % message['message'][:200]
					result += '%s: %s\n%s%s\n#%s (%i %s, %s)\n\n' % (message['login'], '+' * message['count_recom'], tagStr, message['message'], self.numCoding(int(message['post']), params['num_type']), message['count_comments'], self.getText('PS2'), self.getStrTime(message['timestamp'], time_zone = time_zone))
				elif message[0] == const_comment:
					message = message[1]
					mesgAdd = mesgHigh = ''
					if message['high_comment']:
						mesgAdd = ' %s /%s' % (self.getText('PS3'), self.numCoding(int(message['high_comment']), params['num_type']))
					if len(messages) == 1:
						mesgHigh = '>%s\n' % message['high_message']
					result += '%s: %s\n%s%s\n#%s/%s (%s)%s\n\n' % (message['login'], '+' * message['count_recom'], mesgHigh, message['message'], self.numCoding(int(message['post']), params['num_type']) , self.numCoding(message['comment'], params['num_type']), self.getStrTime(message['timestamp'], time_zone = time_zone), mesgAdd)
				elif message[0] == const_user:
					message = message[1]
					result += '%s - %s\n\n' % (message['login'], message['jid'])
			return result
		except:
			log.error('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))

	@timeExecute(1)
	def regUser(self, jid, login, priority = 50, protocol = 'xmpp', force = None):
		try:
			self.db.regUser(jid = jid, login = login, priority = priority, protocol = protocol, force = force)
			return self.getText('MSG3') % login
		except dmbErrorRepeat as exc:
			log.debug('%s, %s' % (self.getText(exc.getText(), 'en'), jid))
			raise dmbErrorRepeat('MSG1')

	@timeExecute(1)
	def unRegUser(self, jid, login):
		self.db.unRegUser(jid = jid, login = login)
		return self.getText('MSG4') % jid

	@timeExecute(1)
	def getLogin(self, jid):
		return self.db.getLogin(jid = jid)

	@timeExecute(1)
	def getJid(self, login, priority = None):
		result = self.db.getJid(login = login)
		if priority:
			return result
		else:
			return result.keys()

	@timeExecute(1)
	def getUserParams(self, login):
		params = self.db.getUserParams(login = login)
		if not params:
			params = {}
		return params

	@timeExecute(1)
	def addPost(self, login, message, tags = [], id_post = None):
		result = self.db.post(login = login, message = message, tags = tags, id_post = id_post)
		try:
			self.db.subscribe(login, post = result)
		except:
			pass
		self.addToQueueSend(user = login, post = result, tag = tags)
		return self.getText('MSG5') % self.numCoding(int(result), self.getUserParams(login).get('num_type', 0))

	@timeExecute(1)
	def addToPost(self, login, post, message = None, tags = []):
		try:
			result = self.db.addToPost(login = login, post = post, message = message, tags = tags)
			try:
				self.db.subscribe(login, post = result)
			except:
				pass
			self.addToQueueSend(user = login, post = result, tag = tags)
			return self.getText('MSG6') % self.numCoding(int(result), self.getUserParams(login)('num_type', 0))
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG1'))

	@timeExecute(1)
	def delPost(self, login, post):
		try:
			self.db.delPost(login = login, post = post)
			return self.getText('MSG7') % self.numCoding(int(post), self.getUserParams(login)('num_type', 0))
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG1'))

	@timeExecute(1)
	def addComment(self, login, message, post, comment = None):
		try:
			result = self.db.comment(login = login, message = message, post = post, comment = comment)
			try:
				self.db.subscribe(login, post = post)
			except:pass
			self.addToQueueSend(user = login, post = post, comment = result)
			num_type = self.getUserParams(login).get('num_type', 0)
			return self.getText('MSG8') % (self.numCoding(int(post), num_type), self.numCoding(int(result), num_type))
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG1'))

	@timeExecute(1)
	def getSubscribes(self, login):
		result = self.db.getSubscribes(login)
		subs_tag = []
		subs_user = []
		for rec in result:
			if rec.has_key('user'):
				subs_user.append(rec['user'])
			elif rec.has_key('tag'):
				subs_tag.append(rec['tag'])
		return self.getText('MSG9') % (', '.join(subs_user), ', '.join(subs_tag))

	@timeExecute(1)
	def addSubscribe(self, login, post = None, tag = None, user = None):
		try:
			if login == user:
				return self.getText('MSG10')
			self.db.subscribe(login = login, post = post, tag = tag, user = user)
			self.delFromUserList(login = login, list_name = 'black', user = user, tag = tag)
			if user:
				self.queue_to_send.append({'jid': self.getJid(user), 'login': user, 'message': self.getText('MSG26', self.getUserParams(user)['locale']) % login})
			return self.getText('MSG11')
		except (dmbErrorRepeat, dmbErrorNotFound) as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG5'))

	@timeExecute(1)
	def delSubscribe(self, login, post = None, tag = None, user = None):
		try:
			self.db.unsubscribe(login = login, post = post, tag = tag, user = user)
			if user:
				self.queue_to_send.append({'jid': self.getJid(user), 'login': user, 'message': self.getText('MSG27', self.getUserParams(user)['locale']) % login})
			return self.getText('MSG12')
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG5'))

	@timeExecute(1)
	def addRecommend(self, login, message = None, post = None, comment = None):
		try:
			result = self.db.recommend(login = login, message = message, post = post, comment = comment)
			if post:
				try:
					self.db.subscribe(login, post = post)
				except:pass
			self.addToQueueSend(user = login, post = post, comment = comment, id_recommend = result)
			return self.getText('MSG13')
		except (dmbErrorRepeat, dmbErrorNotFound) as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG6'))

	@timeExecute(1)
	def getUserList(self, login, list_name = None, to_print = None):
		try:
			lists = self.db.getUserList(login = login, list_name = list_name)
			if to_print:
				if list_name:
					result = ''
					for k, v in lists[list_name].iteritems():
						result += '%s: %s\n' % (k, ', '.join(v))
					return result
				else:
					return self.getText('MSG14') % ', '.join(lists.keys())
			else:
				return lists
		except dmbError as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise exc

	@timeExecute(1)
	def addToUserList(self, login, list_name, user = None, tag = None):
		try:
			self.db.addToUserList(login = login, list_name = list_name, user = user, tag = tag)
			if list_name == 'black':
				try:
					self.delSubscribe(login, user = user, tag = tag)
				except:pass
			return self.getText('MSG15') % list_name
		except (dmbErrorRepeat, dmbErrorNotFound) as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG7'))

	@timeExecute(1)
	def delFromUserList(self, login, list_name, user, tag):
		try:
			self.db.delFromUserList(login = login, list_name = list_name, user = user, tag = tag)
			return self.getText('MSG16') % list_name
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG7'))

	@timeExecute(1)
	def delUserList(self, login, list_name):
		try:
			self.db.delUserList(login, list_name)
			return self.getText('MSG17') % list_name
		except dmbErrorRepeat as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG8'))

	@timeExecute(1)
	def getUserParam(self, login, param = None):
		def transform(param, value):
			if param == 'time_zone':
				d = math.modf(value)
				value = '%i:%02i' % (int(d[1]), int(abs(d[0]*60)))
				return '%s\t%s\n' % (param, value)
			elif param == 'access_level':
				if value == access_allow_all:
					value = 'all'
				elif value == access_deny_black:
					value = 'black'
				elif value == access_allow_white:
					value = 'white'
				elif value == access_deny_all:
					value = 'none'
				return '%s\t%s\n' % (param, value)
			elif param == 'num_type':
				return '%s\t%s\n' % (param, value)
			elif param == 'jids':
				result = ''
				for k, v in value.iteritems():
					result += '\n\t%s (%i)' % (k, int(v))
				return 'jids:%s\n' % result
			elif param == 'locale':
				return '%s\t%s\n' % (param, value)
			else:
				return ''
		params = self.getUserParams(login)
		params['jids'] = self.getJid(login, 1)
		if param:
			if params.has_key(param):
				return transform(param, params.get(param))
			else:
				return self.getText('MSG18') % param
		else:
			result = ''
			for k, v in params.iteritems():
				result += transform(k, v)
			return result

	@timeExecute(1)
	def setUserParam(self, login, param, value = None):
		def info(param):
			if param == 'time_zone':
				return self.getText('PAR1')
			elif param == 'access_level':
				return self.getText('PAR2')
			elif param == 'num_type':
				return self.getText('PAR3')
			elif param == 'locale':
				return self.getText('PAR4') % ', '.join(self.locale.getLocales())
			else:
				return self.getText('MSG18') % param
		def transform(param, value):
			if param == 'time_zone':
				tz = value.split(':')
				try:
					value = float(tz[0])
					if len(tz) > 1 and tz[1].isdigit():
						value += (value/abs(value))*float(tz[1])/60
					return value
				except:
					log.warning('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
					raise dmbErrorParsing
			elif param == 'access_level':
				if value == 'all':
					return access_allow_all
				elif value == 'black':
					return access_deny_black
				elif value == 'white':
					return access_allow_white
				elif value == 'none':
					return access_deny_all
				else:
					raise dmbErrorEmpty
			elif param == 'num_type':
				if value in (self.code_tables.keys()) or value.isdigit():
					return value
			elif param == 'locale':
				return value
		if value:
			value = transform(param, value)
			self.db.setUserParam(login, param, value)
			return self.getText('MSG19') % param
		else:
			return info(param)

	@timeExecute(1)
	def getAlias(self, login, to_print = None):
		result = self.db.getAlias(login = login)
		if to_print:
			prev_user = result_str = ''
			for rec in result:
				if rec['login'] != prev_user:
					prev_user = rec['login']
					if rec['login'] == '*':
						result_str += self.getText('MSG24')
					else:
						result_str += self.getText('MSG25')
				result_str += '\n\t%s\t%s' % (rec['alias'], rec['command'])
			return result_str
		else:
			result_dict = {}
			for rec in result:
				result_dict[rec['alias']] = rec['command']
			return result_dict

	@timeExecute(1)
	def addAlias(self, login, alias, command):
		result = self.db.addAlias(login = login, alias = alias, command = command)
		return self.getText('MSG20') % alias

	@timeExecute(1)
	def delAlias(self, login, alias):
		try:
			self.db.delAlias(login = login, alias = alias)
			return self.getText('MSG21') % alias
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG10'))

	@timeExecute(1)
	def getRegexp(self, login, to_print = None):
		result = self.db.getRegexp(login = login)
		if to_print:
			prev_user = result_str = ''
			for rec in result:
				if rec['login'] != prev_user:
					prev_user = rec['login']
					if rec['login'] == '*':
						result_str += self.getText('MSG24')
					else:
						result_str += self.getText('MSG25')
				result_str += '\n\t%s\t%s\t%s' % (rec['name'], rec['command'], rec['regexp'])
			return result_str
		else:
			result_list = []
			for rec in result:
				result_list.append({'regexp': rec['regexp'], 'command': rec['command']})
			return result_list

	@timeExecute(1)
	def addRegexp(self, login, name, regexp, command):
		try:
			self.db.addRegexp(login = login, name = name, regexp = regexp, command = command)
			return self.getText('MSG22') % name
		except dmbErrorRepeat as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG11'))

	@timeExecute(1)
	def delRegexp(self, login, name):
		try:
			self.db.delRegexp(login = login, name = name)
			return self.getText('MSG23') % name
		except dmbErrorNotFound as exc:
			log.debug(self.getText(exc.getText(), 'en'))
			raise type(exc)(message = self.getText('ERRMSG11'))

	@timeExecute(1)
	def addToSendQueue(self, login, post = None, comment = None, id_recommend = None, message = None):
		return self.db.addToSendQueue(login = login, post = post, comment = comment, id_recommend = id_recommend, message = message)

	@timeExecute(1)
	def delFromSendQueue(self, login):
		return self.db.delFromSendQueue(login)

	@timeExecute(1)
	def getSendQueue(self, login):
		queue = self.db.getSendQueue(login)
		if queue < 0:
			return queue
		result = []
		for rec in queue:
			if rec['post']:
				message = self.getShow(login = login, post = rec['post'], comment = rec['comment'], id_recommend = rec['id_recommend'], error_mesg = None)
				message = self.show(login = rec, messages = message[0], pre_text = message[1])
			else:
				message = rec['message']
			if message:
				result.append(message)
		return result

	@timeExecute(1)
	def getServers(self):
		return list(self.db.getServers())

	@timeExecute(1)
	def addServer(self, server):
		self.db.addServer(server = server)
		return self.getServers()

	@timeExecute(1)
	def delServer(self, server):
		self.db.delServer(server = server)
		return self.getServers()
