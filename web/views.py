from django.http import HttpResponse
from django.shortcuts import render_to_response
from dmb_db.mongodb import dmb_database

def mainPage(request):
	return render_to_response('main.html')

def show(request, post = None):
	if post:
		post = int(post)
		comment = ''
	else:
		post = None
		comment = None
	p = list(dmb_database('localhost').show(count = 10, post = post, comment = comment))
	return render_to_response('posts.html', {'posts': map(lambda x: x[1], filter(lambda x: x[0] == 1, p)), 'comments': map(lambda x: x[1], filter(lambda x: x[0] == 2, p))})
