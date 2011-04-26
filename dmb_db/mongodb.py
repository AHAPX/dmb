# -*- coding: utf-8 -*-

from pymongo import connection, objectid
import time, re
from dmb_main.dmb_log import log
import config
from dmb_main.kernel import *

class dmb_database:
	def __init__(self, host, port = 27017, base = 'dmb', user = None, passwd = None):
		try:
			self.conn = connection.Connection(host, port)[base]
			if self.conn:
				log.info('connected database')
		except:
			log.critical('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
	
	def close(self):
		log.info('disconnected database')

	def initDB(self):
		if not self.conn.params.find({'name': 'counter'}).count():
			self.conn.params.insert({'name': 'counter', 'value': 0})
		if not self.conn.params.find({'name': 's2s_in'}).count():
			self.conn.params.insert({'name': 's2s_in', 'value': s2s_in_allow})
		if not self.conn.params.find({'name': 's2s_reg'}).count():
			self.conn.params.insert({'name': 's2s_reg', 'value': s2s_reg_allow})
		self.conn.users.create_index('login')
		self.conn.users.create_index([('jid', 1), ('priority', -1)])
		self.conn.users.params.create_index('login')
		self.conn.users.lists.create_index('login')
		self.conn.users.alias.create_index('login')
		self.conn.users.regexp.create_index('login')
		self.conn.posts.create_index('login')		
		self.conn.posts.create_index('id')
		self.conn.comments.create_index('login')		
		self.conn.comments.create_index([('post', 1), ('id', 1)])
		self.conn.recommends.create_index('login')		
		self.conn.recommends.create_index([('post', 1), ('comment', 1)])
		self.conn.subscribes.create_index('login')
		self.conn.subscribes.create_index('post')
		self.conn.subscribes.create_index('user')
		self.conn.subscribes.create_index('tag')
		self.conn.send.queue.create_index('login')
		self.conn.send.history.create_index([('login', 1), ('post', 1), ('comment', 1)])
		log.info('create indexes')
		self.regUser('', 'anonymous')
	
	def regUser(self, jid, login, priority = 50, protocol = 'xmpp', force = None):
		if self.conn.users.find({'jid': jid}).count():
			raise dmbErrorRepeat
		elif self.conn.users.find({'login': re.compile('^%s$' % login, re.I|re.U)}).count() and not force:
			raise dmbErrorBusy
		else:
			if not self.conn.users.params.find({'login': login}).count():
				self.conn.users.params.insert({'login': login, 'access_level': access_deny_black, 'time_zone': 0, 'num_type': 0, 'locale': 'en'})
			return self.conn.users.insert({'jid': jid, 'login': login, 'priority': priority, 'protocol': protocol, 'reg_time': time.time()})

	def unRegUser(self, jid, login):
		if self.conn.users.find({'jid': jid, 'login': login}).count():
			self.conn.users.remove({'jid': jid, 'login': login})
			return 1
		else:
			raise dmbErrorNotFound

	def getLogin(self, jid):
		cur = self.conn.users.find_one({'jid': jid})			
		if cur:
			return cur['login']
		else:
			raise dmbErrorAuth

	def getJid(self, login):
		cur = self.conn.users.find({'login': login}).sort('priority', -1)
		if cur.count():
			result = {}
			for rec in cur:
				result[rec['jid']] = rec['priority']
			return result
		else:
			raise dmbErrorNotFound

	def getUserParams(self, login):
		return self.conn.users.params.find_one({'login': login})

	def setUserParam(self, login, param, value):
		self.conn.users.params.update({'login': login}, {'$set': {param: value}})
		return 1

	def post(self, login, message, tags = [], id_post = None):
		if id_post:
			pass
		id_post = self.conn.params.find_and_modify({'name': 'counter'}, {'$inc': {'value': 1}})['value'] + 1
#		id_post = self.conn.params.find_and_modify({'counter': {'$exists': 1}}, {'$inc': {'counter': 1}})['counter'] + 1
		if self.conn.posts.insert({'id': id_post, 'login': login, 'message': message, 'tags': tags, 'timestamp': time.time(), 'count_comments': 0}):
			return id_post

	def addToPost(self, login, post, message = None, tags = []):
		if post:
			cur = self.conn.posts.find({'id': post})
			if cur.count():
				if cur[0]['login'] == login and login != 'anonymous':
					query = {}
					if message:
						query['$set'] = {'message': '%s\n %s' % (cur[0]['message'], message)}
					if tags:
						tags_cur = cur[0]['tags']
						for t in tags:
							if t[0] == '-':
								if tags_cur.count(t[1:]):
									tags_cur.remove(t[1:])
							else:
								if not tags_cur.count(t):
									tags_cur.append(t)
						if query.has_key('$set'):
							query['$set']['tags'] = tags_cur
						else:
							query['$set'] = {'tags': tags_cur}
					if query:
						self.conn.posts.update({'id': post}, query)
						return post
					else:
						raise dmbErrorEmpty
				else:
					raise dmbErrorAccess
			else:
				raise dmbErrorNotFound

	def delPost(self, login, post):
		if post:
			cur = self.conn.posts.find({'id': post})
			if cur.count():
				if cur[0]['login'] == login:
					self.conn.posts.remove({'id': post})
					self.conn.subscribes.remove({'post': post})
					return 1
				else:
					raise dmbErrorAccess
			else:
				raise dmbErrorNotFound

	def comment(self, login, message, post, comment = None):
		cur = self.conn.posts.find({'id': post})
		if cur.count():
			params = self.getUserParams(cur[0]['login'])
			lists = self.getUserList(cur[0]['login'])
			if ((params['access_level'] == access_deny_all) and (login != params['login'])) or ((params['access_level'] == access_deny_black) and (login in lists['black'])) or ((params['access_level'] == access_allow_white) and (not (login in lists['white']))):
				raise dmbErrorAccess
			newComment = {'post': post, 'login': login, 'message': message, 'timestamp': time.time()}
			if comment:
				if not self.conn.comments.find({'id': int(comment), 'post': post}).count():
					raise dmbErrorNotFound
				newComment['comment'] = comment
			next_id = self.conn.posts.find_and_modify({'id': post}, {'$inc': {'count_comments': 1}})['count_comments'] + 1
			newComment['id'] = next_id
			if self.conn.comments.insert(newComment):
				return next_id
		else:
			raise dmbErrorNotFound

	def getComments(self, strSlice):
		if not strSlice:
			return strSlice
		result = []
		comm = []
		strs = unicode(strSlice).split(',')
		for st in strs:
			slic = st.split(':')
			if len(slic) > 1:
				if slic[0] != '' and slic[1] != '':
					for i in range(int(slic[0]), int(slic[1]) + 1):
						comm.append(i)
				elif slic[0] != '':
					result += [{'id': {'$gte': int(slic[0])}}]
				elif slic[1] != '':
					result += [{'id': {'$lte': int(slic[1])}}]
			else:
				comm.append(int(slic[0]))
		if len(comm) > 0:
			result += [{'id': {'$in': comm}}]
		return result

	def show(self, count = 10, login = None, post = None, comment = None, tag = None, user = None):
		if post:
			where = self.getComments(comment)
			cur = self.conn.posts.find({'id': post})
			if not cur.count():
				raise dmbErrorNotFound
			for rec in cur:
				yield (const_post, {'post': post, 'message': rec['message'], 'timestamp': rec['timestamp'], 'login': rec['login'], 'tags': rec['tags'], 'count_comments': rec['count_comments'], 'count_recom': self.conn.recommends.find({'post': post, 'comment': None}).count()})
			if where != None:
				high_message = rec['message']
				query = {'post': post}
				if where:
					query['$or'] = where
				cur = self.conn.comments.find(query)
				if where and not cur.count():
					raise dmbErrorNotFound
				for rec in cur:
					if rec.has_key('comment'):
						r_comment = rec['comment']
						if unicode(comment).isdigit() and r_comment:
							cur_c = self.conn.comments.find({'post': post, 'id': int(r_comment)})
							if cur_c.count():
								high_message = cur_c[0]['message']
					else:
						r_comment = None
					yield (const_comment, {'post': post, 'message': rec['message'], 'timestamp': rec['timestamp'], 'login': rec['login'], 'comment': rec['id'], 'high_comment': r_comment, 'high_message': high_message, 'count_recom': self.conn.recommends.find({'post': post, 'comment': rec['id']}).count()})
		elif user:
			mass = user.split('/')
			cur = self.conn.users.find({'login': mass[0]})
			if not cur.count():
				raise dmbErrorNotFound
			if len(mass) > 1:
				if mass[1] and mass[1].isdigit():
					count = int(mass[1])
				cur = self.conn.posts.find({'login': mass[0]}).sort('timestamp', -1).limit(count)
				seq = list(cur)
				seq.reverse()
				for rec in seq:			
					yield (const_post, {'post': int(rec['id']), 'message': rec['message'], 'timestamp': rec['timestamp'], 'login': rec['login'], 'tags': rec['tags'], 'count_comments': rec['count_comments'], 'count_recom': self.conn.recommends.find({'post': rec['id'], 'comment': None}).count()})
			else:
				yield (const_user, {'login': cur[0]['login'], 'jid': cur[0]['jid']})
		elif tag:			
			query = {'tags': tag}			
			if login:
				params = self.getUserParams(login)
				lists = self.getUserList(login)
				if params['access_level'] == access_deny_black:
					if lists['black']['users']:
						query['login'] = {'$nin': lists['black']['users']}
				elif params['access_level'] == access_allow_white:
					query['login'] = {'$in': [login] + lists['white']['users']}
				elif params['access_level'] == access_deny_all:
					query['login'] = login
			cur = self.conn.posts.find(query).sort('timestamp', -1).limit(count)
			seq = list(cur)
			seq.reverse()
			for rec in seq:			
				yield (const_post, {'post': int(rec['id']), 'message': rec['message'], 'timestamp': rec['timestamp'], 'login': rec['login'], 'tags': rec['tags'], 'count_comments': rec['count_comments'], 'count_recom': self.conn.recommends.find({'post': rec['id'], 'comment': None}).count()})
		else:
			query = {}
			if login:
				params = self.getUserParams(login)
				lists = self.getUserList(login)
				if params['access_level'] == access_deny_black:
					if lists['black']['users']:
						query['login'] = {'$nin': lists['black']['users']}
					if lists['black']['tags']:
						query['$or'] = [{'login': login}, {'tags': {'$nin': lists['black']['tags']}}]
				elif params['access_level'] == access_allow_white:
					query = {'$or': [{'login': login}, {'login': {'$in': lists['white']['users']}, 'tags': {'$in': lists['white']['tags']}}]}
				elif params['access_level'] == access_deny_all:
					query = {'login': login}
			cur = self.conn.posts.find(query).sort('timestamp', -1).limit(count)
			seq = list(cur)
			seq.reverse()
			for rec in seq:			
				yield (const_post, {'post': int(rec['id']), 'message': rec['message'], 'timestamp': rec['timestamp'], 'login': rec['login'], 'tags': rec['tags'], 'count_comments': rec['count_comments'], 'count_recom': self.conn.recommends.find({'post': rec['id'], 'comment': None}).count()})

	def subscribe(self, login, post = None, tag = None, user = None):
		if login == 'anonymous':
			raise dmbErrorAuth
		if post:
			if self.conn.posts.find({'id': post}).count():
				if self.conn.subscribes.find({'login': login, 'post': post}).count():
					raise dmbErrorRepeat
				else:
					return self.conn.subscribes.insert({'login': login, 'post': post})
			else:
				raise dmbErrorNotFound
		elif user:
			if self.conn.users.find({'login': user}).count():
				if self.conn.subscribes.find({'login': login, 'user': user}).count():
					raise dmbErrorRepeat
				else:
					return self.conn.subscribes.insert({'login': login, 'user': user})
			else:
				raise dmbErrorNotFound
		elif tag:
			if self.conn.subscribes.find({'login': login, 'tag': tag}).count():
				raise dmbErrorRepeat
			else:
				return self.conn.subscribes.insert({'login': login, 'tag': tag})
		else:
			raise dmbErrorEmpty

	def unsubscribe(self, login, post = None, tag = None, user = None):
		if post:
			if self.conn.subscribes.find({'login': login, 'post': post}).count():
				self.conn.subscribes.remove({'login': login, 'post': post})
			else:
				raise dmbErrorNotFound
		elif user:
			if self.conn.subscribes.find({'login': login, 'user': user}).count():
				return self.conn.subscribes.remove({'login': login, 'user': user})
			else:
				raise dmbErrorNotFound
		elif tag:
			if self.conn.subscribes.find({'login': login, 'tag': tag}).count():
				return self.conn.subscribes.remove({'login': login, 'tag': tag})
			else:
				raise dmbErrorNotFound
		else:
			raise dmbErrorEmpty

	def getSubscribes(self, login):
			cur = self.conn.subscribes.find({'login': login, 'post': {'$exists': 0}}).sort('tag', 1)
			if cur.count():
				for rec in cur:
					yield rec
			else:
				raise dmbErrorNotFound

	def getSubscribers(self, post, user, comment = None, tag = []):
		query = [{'post': post}]
		if not comment:
			query += [{'user': user}, {'tag': {'$in': tag}}]
		cur = self.conn.subscribes.find({'$or': query})
		if cur.count():
			users = []
			for rec in cur:
				login = rec['login']					
				if (login in users + [user]) or (self.conn.send.history.find({'login': login, 'post': post, 'comment': comment}).count()):
					continue
				params = self.getUserParams(login)
				lists = self.getUserList(login)
				if params['access_level'] == access_deny_black:
					if user in lists['black']['users']:
						continue
				elif params['access_level'] == access_allow_white:
					if not (user in lists['white']['users']):
						continue
				elif params['access_level'] == access_deny_all:
					continue
				users.append(login)
				yield login
		else:
			raise dmbErrorNotFound

	def recommend(self, login, message = None, post = None, comment = None):
		if post:
			cur = self.conn.posts.find({'id': post})
			if cur.count():
				if cur[0]['login'] == login:
					raise dmbErrorRepeat
				newRecomm = {'login': login, 'post': post}
				if comment:
					if self.conn.comments.find({'post': post, 'id': comment}).count():
						newRecomm['comment'] = comment
					else:
						raise dmbErrorNotFound
				if self.conn.recommends.find(newRecomm).count():
					raise dmbErrorRepeat
				else:
					if message:
						newRecomm['message'] = message
					return self.conn.recommends.insert(newRecomm)
			else:
				raise dmbErrorNotFound
		else:
			raise dmbErrorEmpty

	def getRecommend(self, recommend):
		return self.conn.recommends.find_one({'_id': objectid.ObjectId(recommend)})

	def getUserList(self, login, list_name = None):
		query = {'login': login}
		if list_name:
			query['type'] = list_name
		cur = self.conn.users.lists.find(query)
		lists = {}
		for rec in cur:
			if not rec.has_key('tags'):
				rec['tags'] = []
			if not rec.has_key('users'):
				rec['users'] = []
			lists[rec['type']] = {'users': rec['users'], 'tags': rec['tags']}
		if not list_name:
			if not ('black' in lists.keys()): lists['black'] = {'tags': [], 'users': []}
			if not ('white' in lists.keys()): lists['white'] = {'tags': [], 'users': []}
		elif not lists:
			lists = {list_name: {'tags': [], 'users': []}}
		return lists

	def addToUserList(self, login, list_name, user = None, tag = None):
		if user:
			if self.conn.users.find({'login': user}).count():
				obj_type, obj_name = 'users', user
			else:
				raise dmbErrorNotFound
		elif tag:
			obj_type, obj_name = 'tags', tag
		else:
			raise dmbErrorEmpty
		if self.conn.users.lists.find({'login': login, obj_type: obj_name, 'type': list_name}).count():
			raise dmbErrorRepeat
		else:
			if list_name == 'white':
				if self.conn.users.lists.find({'login': login, 'type': 'black', obj_type: obj_name}).count():
					self.conn.users.lists.update({'login': login, 'type': 'black'}, {'$pull': {obj_type: obj_name}})
			elif list_name == 'black':
				if self.conn.users.lists.find({'login': login, 'type': 'white', obj_type: obj_name}).count():
					self.conn.users.lists.update({'login': login, 'type': 'white'}, {'$pull': {obj_type: obj_name}})
			if self.conn.users.lists.find({'login': login, 'type': list_name}).count():
				return self.conn.users.lists.update({'login': login, 'type': list_name}, {'$push': {obj_type: obj_name}})
			else:
				return self.conn.users.lists.insert({'login': login, obj_type: [obj_name], 'type': list_name})

	def delFromUserList(self, login, list_name, user = None, tag = None):
		if user and self.conn.users.find({'login': user}).count():
			obj_type, obj_name = 'users', user
		elif tag:
			obj_type, obj_name = 'tags', tag
		else:
			raise dmbErrorEmpty
		if self.conn.users.lists.find({'login': login, obj_type: obj_name, 'type': list_name}).count():
			self.conn.users.lists.update({'login': login, 'type': list_name}, {'$pull': {obj_type: obj_name}})
		else:
			raise dmbErrorNotFound

	def delUserList(self, login, list_name):
		if self.conn.users.lists.find({'login': login, 'type': list_name}).count():
			self.conn.users.lists.remove({'login': login, 'type': list_name})
		else:
			raise dmbErrorNotFound

	def getAlias(self, login):
		cur = self.conn.users.alias.find({'login': {'$in': ['*', login]}}).sort('login', -1)
		for rec in cur:
			yield rec

	def addAlias(self, login, alias, command):
		if self.conn.users.alias.find({'login': login, 'alias': alias}).count():
			self.conn.users.alias.update({'login': login, 'alias': alias}, {'$set': {'command': command}})
			return 1
		else:
			return self.conn.users.alias.insert({'login': login, 'alias': alias, 'command': command})

	def delAlias(self, login, alias):
		if self.conn.users.alias.find({'login': login, 'alias': alias}).count():
			self.conn.users.alias.remove({'login': login, 'alias': alias})
			return 1
		else:
			raise dmbErrorNotFound

	def getRegexp(self, login):
		cur = self.conn.users.regexp.find({'login': {'$in': ['*', login]}}).sort('login', -1)
		for rec in cur:
			yield rec

	def addRegexp(self, login, name, regexp, command):
		if self.conn.users.regexp.find({'login': login, '$or': [{'name': name}, {'regexp': regexp}]}).count():
			raise dmbErrorRepeat
		else:
			return self.conn.users.regexp.insert({'login': login, 'name': name, 'regexp': regexp, 'command': command})

	def delRegexp(self, login, name):
		if self.conn.users.regexp.find({'login': login, 'name': name}).count():
			self.conn.users.regexp.remove({'login': login, 'name': name})
			return 1
		else:
			raise dmbErrorNotFound

	def addToSendHistory(self, login, post, comment = None):
		return self.conn.send.history.insert({'login': login, 'post': post, 'comment': comment})

	def addToSendQueue(self, login, post = None, comment = None, id_recommend = None, message = None):
		if self.conn.send.queue.find({'login': login, 'post': post, 'comment': comment, 'message': message}).count():
			raise dmbErrorRepeat
		else:
			return self.conn.send.queue.insert({'login': login, 'post': post, 'comment': comment, 'id_recommend': id_recommend, 'message': message})

	def delFromSendQueue(self, login):
		self.conn.send.queue.remove({'login': login})
		return 1

	def getSendQueue(self, login):
		cur = self.conn.send.queue.find({'login': login}).sort('post', 1)
		if cur.count():
			for rec in cur:
				yield rec
		else:
			raise dmbErrorNotFound

	def getServers(self):
		for rec in self.conn.servers.find():
			yield rec['name']

	def addServer(self, server):
		if self.conn.servers.find({'name': server}).count():
			raise dmbErrorRepeat
		else:
			return self.conn.servers.insert({'name': server})

	def delServer(self, server):
		if self.conn.servers.find({'name': server}).count():
			self.conn.servers.remove({'name': server})
			return 1
		else:
			raise dmbErrorNotFound

