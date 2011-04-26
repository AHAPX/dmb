# -*- coding: utf8 -*-

import MySQLdb
import time, re, sys
from dmb_main.dmb_log import log
import config
from dmb_main.kernel import *

class dmb_database:
	def __init__(self, host, port = 3306, base = 'dmb', user = None, passwd = None):
		try:
			self.conn = MySQLdb.connect(host = host, user = user, passwd = passwd, db = base)
			if self.conn:
				log.info('connected database')
		except:
			log.critical('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
	
	def close(self):
		self.conn.close()
		log.info('disconnected database')
	
	def initDB(self):
		'''Создает все служебные таблицы'''
		try:
			self.conn.query('''
			begin;
				create table types (id int not null, type varchar(15), primary key (id)) engine=InnoDB;
				create table users (id int not null auto_increment, login varchar(50), primary key (id)) engine=InnoDB;
				create table users_params (id int not null auto_increment, id_user int, id_type int, value varchar(15), primary key (id)) engine=InnoDB;
				create table users_lists (id int not null auto_increment, id_user int, name varchar(15), id_type int, id_object int, primary key (id)) engine=InnoDB;
				create table users_alias (id int not null auto_increment, id_user int, alias varchar(15), command varchar(50), primary key (id)) engine=InnoDB;
				create table users_regexp (id int not null auto_increment, id_user int, name varchar(15), exp varchar(100), command varchar(50), primary key (id)) engine=InnoDB;
				create table users_jids (id int not null auto_increment, id_user int, jid varchar(100), protocol varchar(10), priority int, primary key (id)) engine=InnoDB;
				create table posts (id int not null auto_increment, id_user int, message text, datetime timestamp, primary key (id)) engine=InnoDB;
				create table tags (id int not null auto_increment, tag varchar(30), primary key (id)) engine=InnoDB;
				create table posts_tags (id int not null auto_increment, id_post int, id_tag int, primary key (id)) engine=InnoDB;
				create table comments (id int not null, id_user int, id_post int not null, id_comment int null, message text, datetime timestamp, primary key (id, id_post)) engine=InnoDB;
				create table subscribes (id int not null auto_increment, id_user int, id_type int, id_object int, primary key(id)) engine=InnoDB;
				create table recommends (id int not null auto_increment, id_user int, it_type int, id_object int, message varchar(50), primary key (id)) engine=InnoDB;
				create table send_history (id int not null auto_increment, id_user int, id_post int, id_comment int, primary key (id)) engine=InnoDB;
				create table send_queue (id int not null auto_increment, id_user int, id_post int, id_recommend int, primary key (id)) engine=InnoDB;
				create table servers (id int not null auto_increment, name varchar(30), primary key (id)) engine=InnoDB;
				insert into types values (1, 'user'), (2, 'post'), (3, 'comment'), (4, 'tag'), (10, 'num_type'), (11, 'time_zone'), (12, 'access_level'), (13, 'locale');
				insert into users (login) values ('anonymous'), ('*');
			commit;''')
			log.info('tables created success')
		except MySQLdb.OperationalError:
			log.info('tables already exists')
			raise dmbErrorRepeat
			
	def regUser(self, jid, login, priority = 50, protocol = 'xmpp', force = None):
		'''Регистрация пользователя'''
		cur = self.conn.cursor()
		cur.execute('select * from users_jids where jid = \'%s\'' % jid)
		if cur.rowcount:
			raise dmbErrorRepeat
		else:
			cur.execute('select * from users where login = \'%s\'' % login)
			if cur.rowcount > 0 and not force:
				raise dmbErrorBusy
		self.conn.query('''
		begin;
			insert into users (login) values ('%(login)s');
			select @id_user := id from users where login = '%(login)s';
			insert into users_jids (id_user, jid, protocol, priority) values (@id_user, '%(jid)s', '%(protocol)s', %(priority)i);
			insert into users_params (id_user, id_type, value) values (@id_user, 10, '0'), (@id_user, 11, '0'), (@id_user, 12, '%(access)i'), (@id_user, 13, 'en');
		commit;''' % {'login': login, 'jid': jid, 'protocol': protocol, 'priority': priority, 'access': access_deny_black})
		cur = self.conn.cursor()
		cur.execute('select id from users where login = \'%s\'' % login)
		return cur.fetchone()[0]

	def unRegUser(self, jid, login):
		cur = self.conn.cursor()
		cur.execute('select j.id from users u join users_jids j on j.id_user = u.id where j.jid = \'%s\' and u.login = \'%s\'' % (jid, login))
		if cur.rowcount:
			self.conn.query('delete from users_jids where jid = \'%s\'' % jid)
			self.conn.commit()
			return 1
		else:
			raise dmbErrorNotFound

	def getLogin(self, jid):
		cur = self.conn.cursor()
		cur.execute('select u.login from users u join users_jids j on j.id_user = u.id where j.jid = \'%s\'' % jid)
		if cur.rowcount:
			return cur.fetchone()[0]
		else:
			raise dmbErrorAuth

	def getJid(self, login):
		cur = self.conn.cursor()
		cur.execute('select jid, priority from users_jids where id_user = (select id from users where login = \'%s\') order by priority desc;' % login)
		if cur.rowcount:
			result = {}
			for rec in cur:
				result[rec[0]] = rec[1]
			return result
		else:
			raise dmbErrorNotFound

	def getUserParams(self, login):
		cur = self.conn.cursor()
		cur.execute('select t.type, p.value from users u join users_params p on p.id_user = u.id join types t on t.id = p.id_type where u.login = \'%s\';' % login)
		result = {}
		for rec in cur:
			result[rec[0]] = rec[1]
		return result

	def setUserParam(self, login, param, value):
		self.conn.query('update users_params set value = \'%(value)s\' where id_user = (select id from users where login = \'%(login)s\') and id_type = (select id from types where type = \'%(param)s\');' % {'login': login, 'param': param, 'value': value})
		self.conn.commit()
		return 1

	def post(self, message, tags, login = None, jid = None):
		'''Добавление нового поста'''
		cur = self.conn.cursor()
		id_user = self.getUser(login, jid)
		if id_user < 0:
			return id_user
		id_tags = []
		for tag in tags:
			cur.execute('select id from tags where name = \'%s\'' % tag)
			if cur.rowcount > 0:
				id_tag = cur.fetchone()[0]
			else:
				self.conn.query('insert into tags (name) values (\'%s\')' % tag)
				id_tag = self.conn.insert_id()
			id_tags.append(id_tag)
		self.conn.query('insert into posts (id_user, message, datetime) values (%i, \'%s\', now())' % (id_user, message))
		id_post = self.conn.insert_id()
		for id_tag in id_tags:
			self.conn.query('insert into post_tags (id_post, id_tag) values (%i, %i)' % (id_post, id_tag))
		return id_post
	
	def comment(self, post, message, login = None, jid = None):
		'''Добавление комментария к посту'''
		cur = self.conn.cursor()
		id_user = self.getUser(login, jid)
		if id_user < 0:
			return id_user
		if post:
			mass = str(post).split('/')
			cur.execute('select ifnull(max(id), 0) from comments where id_post = %s' % mass[0])
			next_id = int(cur.fetchone()[0]) + 1
			if len(mass) > 1:
				id_post = int(mass[0])
				id_comment = int(mass[1])
				self.conn.query('insert into comments (id, id_post, id_user, id_comment, message, datetime) values (%i, %i, %i, %i, \'%s\', now())' % (next_id, id_post, id_user, id_comment, message))
			else:
				id_post = int(post)
				self.conn.query('insert into comments (id, id_post, id_user, message, datetime) values (%i, %i, %i, \'%s\', now())' % (next_id, id_post, id_user, message))
			return self.conn.insert_id()
		else:
			return -5
	
	def getComments(self, strSlice):
		'''Преобразование среза комментариев к строке, которую можно использовать в where запроса'''
		result = ''
		comm = []
		strs = strSlice.split(',')
		for st in strs:
			slic = st.split(':')
			if len(slic) > 1:
				if slic[0] != '' and slic[1] != '':
					for i in range(int(slic[0]), int(slic[1]) + 1):
						comm.append(i)
				elif slic[0] != '':
					if result != '': result += ' or '
					result += 'c.id >= %s' % slic[0]
				elif slic[1] != '':
					if result != '': result += ' or '
					result += 'c.id <= %s' % slic[1]
			else:
				comm.append(int(slic[0]))
		if len(comm) > 0:
			st = ''
			if result != '': result += ' or '
			for i in comm:
				if st != '': st += ','
				st += str(i)
			result += 'c.id in (%s)' % st
		if result != '': result = ' and (%s)' % result
		return result

	def show(self, count = 10, post = None, login = None):
		'''Возвращает список постов, комментариев и информации о пользователе'''
		cur = self.conn.cursor()
		result = []
		if post:
#	Получаем пост и комментарии по нему
			mass = str(post).split('/')
			if len(mass) > 1:
				id_post = int(mass[0])
				if mass[1] != '':
					where = self.getComments(mass[1])
				else:
					where = ''
			else:
				id_post = int(post)
				where = None
			if not where:
				cur.execute('select p.id, p.message, p.datetime, u.login, (select count(*) from comments c where c.id_post = p.id) as comments from posts p join users u on u.id = p.id_user where p.id = %i' % id_post)
				for record in cur.fetchall():
					result.append((const_post, record))
			if where != None:
				cur.execute('select c.id_post, c.message, c.datetime, u.login, c.id, c.id_comment from comments c join users u on u.id = c.id_user where c.id_post = %i%s' % (id_post, where))
				for record in cur.fetchall():
					result.append((const_comment, record))
		elif login:
#	Получаем описание пользователя
			mass = login.split('/')
			if len(mass) > 1:
				if mass[1] and unicode(mass[1]).isdecimal():
					count = int(mass[1])
				cur.execute('select p.id, p.message, p.datetime, u.login, (select count(*) from comments c where c.id_post = p.id) as comments from posts p join users u on u.id = p.id_user where u.login = \'%s\' order by p.datetime desc limit %i;' % (mass[0], count))
				seq = []
				for record in cur.fetchall():
					seq.append((const_post, record))
				seq.reverse()
				result += seq
			else:
				cur.execute('select id, login, jid from users where login = \'%s\'' % login)
				result.append((const_user, cur.fetchone()))
		else:
#	Получаем список последних постов
			cur.execute('select p.id, p.message, p.datetime, u.login, (select count(*) from comments c where c.id_post = p.id) as comments from posts p join users u on u.id = p.id_user order by p.datetime desc limit %i' % count)
			seq = []
			for record in cur.fetchall():
				seq.append((const_post, record))
			seq.reverse()
			result += seq
		return result

	def subscribe(self, post = None, tag = None, user = None, login = None, jid = None):
		'''Подписывает пользователя на пост, тег или посты другого пользователя'''
		cur = self.conn.cursor()
		id_subs_user = self.getUser(login, jid)
		if id_subs_user < 0:
			return id_subs_user
		if user:
			cur.execute('select id from users where login = \'%s\'' % user)
			if cur.rowcount > 0:
				id_user = int(cur.fetchone()[0])
			else:
				return -11
			cur.execute('select id from subscribes where id_subs_user = %i and id_user = %i' % (id_subs_user, id_user))
			if cur.rowcount > 0:
				return -21
			else:
				self.conn.query('insert into subscribes (id_user, id_subs_user) value (%i, %i)' % (id_user, id_subs_user))
		elif post:
			cur.execute('select id from posts where id = %i' % post)
			if cur.rowcount <= 0:
				return -12
			cur.execute('select id from subscribes where id_subs_user = %i and id_post = %i' % (id_subs_user, post))
			if cur.rowcount > 0:
				return -22
			else:
				self.conn.query('insert into subscribes (id_post, id_subs_user) value (%i, %i)' % (post, id_subs_user))
		elif tag:
			cur.execute('select id from tags where name = \'%s\'' % tag)
			if cur.rowcount > 0:
				id_tag = int(cur.fetchone()[0])
			else:
				self.conn.query('insert into tags (name) value (\'%s\')' % tag)
				id_tag = self.conn.insert_id()
			cur.execute('select id from subscribes where id_subs_user = %i and id_tag = %i' % (id_subs_user, id_tag))
			if cur.rowcount > 0:
				return -23
			else:
				self.conn.query('insert into subscribes (id_tag, id_subs_user) value (%i, %i)' % (id_tag, id_subs_user))
		else:
			return -15
		return self.conn.insert_id()

	def recommend(self, message = None, post = None, comment = None, login = None, jid = None):
		'''Рекоммендует посты и комментарии'''
		cur = self.conn.cursor()
		id_user = self.getUser(login, jid)
		if id_user < 0:
			return id_user
		if post:
			cur.execute('select id from posts where id = %i' % post)
			if cur.rowcount <= 0:
				return -11
			if comment:
				cur.execute('select id from comments where id = %i and id_post = %i' % (comment, post))
				if cur.rowcount <= 0:
					return -12
			else:
				comment = 'null'
			if comment == 'null':
				op_str = 'is'
			else:
				op_str = '='
			cur.execute('select id from recommends where id_post = %i and id_comment %s %s and id_user = %i' % (post, op_str, comment, id_user))
			if cur.rowcount > 0:
				return -15
			if message:
				message = '\'%s\'' % message
			else:
				message = 'null'
			self.conn.query('insert into recommends (id_post, id_comment, id_user, message) values (%i, %s, %i, %s)' % (post, comment, id_user, message))
			return self.conn.insert_id()
		else:
			return -10














