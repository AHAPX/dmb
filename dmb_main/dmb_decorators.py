import time
from dmb_log import log_cntr

def timeExecute(m = 0):
	def decorate(f):
		def wrapper(*args, **kwargs):
			time_tick = time.time()
			result = f(*args, **kwargs)
			log_cntr.info('%s %s %s %s' % (f.__name__, args[m:], kwargs, time.time()-time_tick))
			return result
		return wrapper
	return decorate
