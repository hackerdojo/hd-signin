#!/usr/bin/env python
 
import wsgiref.handlers
 
from google.appengine.api.labs import taskqueue
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import mail
from google.appengine.ext.webapp.util import login_required
from datetime import datetime
import urllib, hashlib, time
from django.utils import simplejson

PBWORKS_TOKEN = None
def get_token(refresh=False):
	global PBWORKS_TOKEN
	if refresh or not PBWORKS_TOKEN:
		response = urlfetch.fetch('http://dojo.pbworks.com/api_v2/op/Login/email/appenginebot%40hackerdojo.com/password/botbotbot/_type/jsontext').content
		PBWORKS_TOKEN = parse_json(response)['token']
	return PBWORKS_TOKEN

def parse_json(data):
	return simplejson.loads(data.replace('/*-secure-','').replace('*/', ''))

def broadcast(**message):
	urlfetch.fetch('http://live.readyinrealtime.com/hackerdojo-signin', method='POST', payload=urllib.urlencode(message))

class Signin(db.Model):
	email = db.StringProperty(required=True)
	hash = db.StringProperty()
	name = db.StringProperty()
	image_url = db.StringProperty()
	type = db.StringProperty(required=True)
	created = db.DateTimeProperty(auto_now_add=True)
	active = db.BooleanProperty(default=True)

	@classmethod
	def get_active_staff(cls):
		return cls.all().filter('type IN', ['StaffKey', 'StaffNoKey']).filter('active =', True).order('-created')
	
	@classmethod
	def deactivate_staffer(cls, email):
		staffer = cls.get_active_staff().filter('email =', email).get()
		staffer.active = False
		staffer.put()
	
	def name_or_nick(self):
		return self.name or self.email.split('@')[0]

class MainHandler(webapp.RequestHandler):
	def get(self):
		self.response.out.write(template.render('templates/main.html', locals()))
	
	def post(self):
		email = self.request.get('email')
		if not '@' in email:
			email = '%s@hackerdojo.com' % email
		if email:
			hash=hashlib.md5(email).hexdigest()
			response = urlfetch.fetch('https://dojo.pbworks.com/api_v2/op/GetUserInfo/_type/jsontext/email/%s/token/%s' % (urllib.quote(email), get_token())).content
			if not 'appenginebot' in response:
				response = parse_json(response)
				image = response['image']
				name = response['name']
			else:
				image = 'http://0.gravatar.com/avatar/%s' % hash
				name = None
			s = Signin(email=email, type=self.request.get('type'), image_url=image, name=name)
			s.put()
			if name:
				broadcast(cmd='say', text='Welcome back, %s' % s.name_or_nick().split(' ')[0])
			else:
				broadcast(cmd='say', text='Welcome to Hacker Dojo!')
		self.redirect('/')

class StaffHandler(webapp.RequestHandler):
	def get(self):
		staff = Signin.get_active_staff()
		self.response.out.write(template.render('templates/staff.html', locals()))
	
	def post(self):
		email = self.request.get('email')
		if email:
			Signin.deactivate_staffer(email)
		self.redirect('/staff')

class TokenHandler(webapp.RequestHandler):
	def get(self):
		get_token(True)
		self.response.out.write("ok")

def main():
    application = webapp.WSGIApplication([
        ('/', MainHandler), 
		('/staff', StaffHandler),
		('/refreshtoken', TokenHandler),
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)
 
if __name__ == '__main__':
    main()
 