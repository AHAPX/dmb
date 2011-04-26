# -*- coding: utf-8 -*-

from getopt import *
from kernel import *
import sys, re
from dmb_log import log

command_list = ['show', 'post', 'comment', 'delete', 'recommend', 'subscribes', 'unsubscribe', 'register', 'unregister', 'list', 'get', 'set', 'alias', 'regexp']

def parsing(service, login, text, jid = None):
	try:
		command, args = text.split(' ')[0].lower(), text.split(' ')[1:]
		if not (command in command_list):
			alias = service.getAlias(login = login)
			if alias.has_key(command):
				command, args = alias.get(command).split(' ')[0], alias.get(command).split(' ')[1:] + args
			else:
				regexp = service.getRegexp(login = login)
				go_exit = 1
				for r in regexp:
					m = re.compile(r['regexp'], re.U).match(text)
					if m:
						result = r['command']
						noname = ''
						for k, v in m.groupdict().iteritems():
							if k!='noname' and v:
								result += ' --%s=%s' % (k, v)
							elif v:
								noname = ' %s' % v
						result += noname
						command, args = result.split(' ')[0], result.split(' ')[1:]
						go_exit = 0
						break
				if go_exit:
					raise dmbErrorParsing
		log.debug('%s %s' % (command, args))
		if login == 'anonymous' and not command in ('show', 'post', 'comment', 'register'):
			return service.getText('MSG70')
		if command == 'show':
			user = post = comment = tag = None
			count = 10
			opts, args = getopt(args, 'u:p:t:', ['user=', 'post=', 'tags='])
			for o, a in opts:
				if o in ('-u', '--user'):
					user = a
					break
				elif o in ('-p', '--post'):
					post = a
					break
				elif o in ('-t', '--tags'):
					tag = a
					break
			for a in args:
				if a.isdigit():
					count = int(a)
					break
			if post:
				post, comment = service.normilizeID(post)
			return service.show(login = login, count = count, post = post, comment = comment, tag = tag, user = user)
		elif command == 'post':
			post = message = None
			tags = []
			opts, args = getopt(args, 'p:t:a', ['post=', 'tags=', 'anonymous'])
			for o, a in opts:
				if o in ('-p', '--post'):
					post = a
				elif o in ('-t', '--tags'):
					tags = a.split(',')
				elif o in ('-a', '--anonymous'):
					login = 'anonymous'
			if tags.count(''):
				tags.remove('')
			message = ' '.join(args)
			if post:
				return service.addToPost(login = login, post = int(post), message = message, tags = tags)
			else:
				return service.addPost(login = login, message = message, tags = tags)
		elif command == 'comment':
			post = comment = None
			opts, args = getopt(args, 'ap:', ['post=', 'anonymous'])
			for o, a in opts:
				if o in ('-p', '--post'):
					post = a
				elif o in ('-a', '--anonymous'):
					login = 'anonymous'
			if post:
				post, comment = service.normilizeID(post)
				message = ' '.join(args)
				return service.addComment(login = login, post = post, comment = comment, message = message)
			else:
				raise dmbErrorParsing
		elif command == 'delete':
			post = None
			opts, args = getopt(args, 'p:', ['post='])
			for o, a in opts:
				if o in ('-p', '--post'):
					post = service.normilizeID(a)[0]
			if post:
				return service.delPost(login = login, post = post)
			else:
				raise dmbErrorParsing
		elif command == 'recommend':
			post = message = None
			opts, args = getopt(args, 'p:', ['post='])
			for o, a in opts:
				if o in ('-p', '--post'):
					post = a
			message = ' '.join(args)
			if post:
				post, comment = service.normilizeID(post)
				if args:
					message = ' '.join(args)
				return service.addRecommend(login = login, message = message, post = post, comment = comment)
			else:
				raise dmbErrorParsing
		elif command == 'subscribes':
			return service.getSubscribes(login = login)
		elif command == 'subscribe':
			user = post = tag = None
			opts, args = getopt(args, 'u:p:t:', ['user=', 'post=', 'tag='])
			for o, a in opts:
				if o in ('-u', '--user'):
					user = a
					break
				elif o in ('-p', '--post'):
					post = a
					break
				elif o in ('-t', '--tag'):
					tag = a
					break
			if post:
				post = service.normilizeID(post)[0]
			return service.addSubscribe(login = login, post = post, tag = tag, user = user)
		elif command == 'unsubscribe':
			user = post = tag = None
			opts, args = getopt(args, 'u:p:t:', ['user=', 'post=', 'tag='])
			for o, a in opts:
				if o in ('-u', '--user'):
					user = a
					break
				elif o in ('-p', '--post'):
					post = a
					break
				elif o in ('-t', '--tag'):
					tag = a
					break
			if post:
				post = service.normilizeID(post)[0]
			return service.delSubscribe(login = login, post = post, tag = tag, user = user)
		elif command == 'register':
			priority = 50
			opts, args = getopt(args, 'j:p:', ['jid=', 'priority='])
			for o, a in opts:
				if o in ('-j', '--jid'):
					jid = a
				elif o in ('-p', '--priority'):
					priority = int(a)
			if login == 'anonymous' and len(args) > 0:
				login = args.split()[0]
				if not re.search(r'^\w+$', login):
					raise dmbError('MSG72')
				force = None
			else:
				force = 1
			return service.regUser(jid = jid, login = login, priority = priority, force = force)
		elif command == 'unregister':
			jid_d = None
			opts, args = getopt(args, 'j:', ['jid='])
			for o, a in opts:
				if o in ('-j', '--jid'):
					jid_d = a
			if jid_d != jid:
				return service.unRegUser(jid = jid_d, login = login)
			else:
				return service.getText('MSG71')
		elif command == 'list':
			add = 1
			is_tag = 0
			list_name = user = tag = None
			opts, args = getopt(args, 'adl:t', ['add', 'delete', 'list=', 'tag'])
			for o, a in opts:
				if o in ('-a', '--add'):
					add = 1
				elif o in ('-d', '--delete'):
					add = 0
				elif o in ('-t', '--tag'):
					is_tag = 1
				elif o in ('-l', '--list'):
					if not list_name:
						list_name = a
			if len(args) > 0:
				if is_tag:
					tag = args.split()[0]
				else:
					user = args.split()[0]
			if list_name:				
				if tag or user:
					if add:
						return service.addToUserList(login = login, list_name = list_name, user = user, tag = tag)
					else:
						return service.delFromUserList(login = login, list_name = list_name, user = user, tag = tag)
				elif not add:
					return service.delUserList(login = login, list_name = list_name)
				else:
					return service.getUserList(login = login, list_name = list_name, to_print = 1)
			else:
				return service.getUserList(login = login, to_print = 1)
			raise dmbErrorParsing
		elif command == 'get':
			if len(args) > 0:
				param = args.split()[0]
			else:
				param = None
			return service.getUserParam(login, param)
		elif command == 'set':
			if len(args) > 0:
				param = args.split()[0]
				if len(args) > 1:
					value = args[1]
				else:
					value = None
				return service.setUserParam(login, param, value)
			else:
				raise dmbErrorParsing
		elif command == 'alias':
			add = 1
			name = command = None
			opts, args = getopt(args, 'adn:', ['add', 'delete', 'name='])
			for o, a in opts:
				if o in ('-a', '--add'):
					add = 1
				elif o in ('-d', '--delete'):
					add = 0
				elif o in ('-n', '--name'):
					name = a
			command = ' '.join(args)
			if not name:
				return service.getAlias(login = login, to_print = 1)
			else:
				if add:
					return service.addAlias(login = login, alias = name, command = command)
				else:
					return service.delAlias(login = login, alias = name)
			raise dmbErrorParsing
		elif command == 'regexp':
			add = 1
			name = regexp = command = None
			opts, args = getopt(args, 'adn:c:', ['add', 'delete', 'name=', 'command='])
			for o, a in opts:
				if o in ('-a', '--add'):
					add = 1
				elif o in ('-d', '--delete'):
					add = 0
				elif o in ('-n', '--name'):
					name = a
				elif o in ('-c', '--command'):
					command = a
			regexp = ' '.join(args)
			if not name:
				return service.getRegexp(login = login, to_print = 1)
			else:
				if add:
					return service.addRegexp(login = login, name = name, regexp = regexp, command = command)
				else:
					return service.delRegexp(login = login, name = name)
			raise dmbErrorParsing
		else:
			raise dmbErrorParsing
	except GetoptError:
		log.warning('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
		raise dmbErrorCommand
	except TypeError:
		log.warning('%d %s %s' % (sys.exc_traceback.tb_lineno, sys.exc_type, sys.exc_value))
		raise dmbErrorParsing

def adminParsing(service, login, text, jid = None):
	try:
		command, args = text.split(' ', 1)
	except ValueError:
		command, args = text.split(' ', 1)[0], None
	log.debug('%s %s' % (command, args))
	if command == 'exit':
		sys.exit()
	elif command == 'registry':
		new_server = args.split(' ')[0]
		dmb_servers = service.addServer(new_server)
		service.queue_to_send.append({'jid': (new_server,), 'message': 'registry', 'send': True, 'extra': {'dmb': 'server'}})
	elif command == 'add_server':
		try:
			dmb_servers = service.addServer(args.split()[0])
			return 'ok'
		except dmbErrorRepeat:
			return 'already exists'
	elif command == 'del_server':
		try:
			dmb_servers = service.delServer(args.split()[0])
			return 'ok'
		except dmbErrorNotFound:
			return 'not found'
	elif command == '*':
		return parsing(service, '*', ' '.join(args), jid)
	else:
		return parsing(service, login, text, jid)
