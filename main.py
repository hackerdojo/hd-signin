#!/usr/bin/env python
 
import wsgiref.handlers
 
from google.appengine.api.labs import taskqueue
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext.webapp import template
from google.appengine.ext import deferred
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import mail
from google.appengine.ext.webapp.util import login_required
from datetime import tzinfo, datetime, timedelta
import urllib, hashlib, time, random
import logging, email
from google.appengine.ext import webapp 
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail
import json
import math
import pprint
import string
import util
from util import Pacific
import os
from quix.pay.gateway.authorizenet import AimGateway
from quix.pay.transaction import CreditCard
from keys import auth_net_login_id, auth_net_trans_key

MAX_SIGNIN_TIME = 60 * 60 * 8

def parse_json(data):
  return json.loads(data.replace('/*-secure-','').replace('*/', ''))

class DoorLog(db.Model):
  event_time = db.DateTimeProperty(auto_now_add=True)
  door = db.StringProperty()
  rfid_tag = db.StringProperty()
  username = db.StringProperty()
  status = db.StringProperty()

class Donation(db.Model):
  amount = db.FloatProperty()
  donation_time = db.DateTimeProperty(auto_now_add=True)
  transaction_id = db.StringProperty()
  name = db.StringProperty()
  status = db.StringProperty()
  status_code = db.IntegerProperty()

# An event. Usually contains zero rows ("regular mode") or ONE row ("event mode")
class Event(db.Model):
  event_name = db.StringProperty()
  logo_url = db.StringProperty()
  from_time = db.DateTimeProperty()
  to_time = db.DateTimeProperty()
  webhook_url = db.StringProperty()
  custom_html = db.TextProperty()

  @classmethod
  def get_current_event(cls):
    current_event = cls.all().get()
    return current_event

  @classmethod
  def delete_current_event(cls):
    current_event = cls.all().get()
    if current_event:
      current_event.delete()
  
# Configure a special event
class EventModeHandler(webapp.RequestHandler):
  def get(self):
    current_event = Event.get_current_event()
    now = datetime.now().strftime("%Y-%m-%d %X")
    self.response.out.write(template.render('templates/eventmode.html', locals()))

  def post(self):
    Event.delete_current_event()
    new_event = Event(
      event_name=self.request.get('event_name'),
      logo_url=self.request.get('logo_url'),
      from_time=datetime.strptime(self.request.get("from_time"), "%Y-%m-%d %X"),
      to_time= datetime.strptime(self.request.get("to_time"), "%Y-%m-%d %X"),
      webhook_url=self.request.get('webhook_url'),
      custom_html=self.request.get('custom_html')
    )
    new_event.put()
    self.redirect('/eventmode')
    

class DailyCount(db.Model):
  day = db.DateProperty(required=True)
  count = db.IntegerProperty(required=True)
    
  @classmethod
  def get(cls):
    count_rec = cls.all().filter('day =', datetime.now(Pacific()).date()).get()
    if count_rec:
        count = count_rec.count
    else:
        count = 0
    return count

  @classmethod
  def increment_and_get(cls):
    count_rec = cls.all().filter('day =', datetime.now(Pacific()).date()).get()
    if count_rec:
        count_rec.count = count_rec.count + 1
    else:
        count_rec = DailyCount(day=datetime.now(Pacific()).date(),count=1)
    count_rec.put()
    return count_rec.count  

    
# A log of all signins.  One row per signin.
class Signin(db.Model):
  email = db.StringProperty(required=True)
  hash = db.StringProperty()
  name = db.StringProperty()
  image_url = db.StringProperty()
  type = db.StringProperty(required=True)
  created = db.DateTimeProperty(auto_now_add=True)
  closed = db.DateTimeProperty()
  time_delta = db.IntegerProperty()
  active = db.BooleanProperty(default=True)

  @classmethod
  def get_active_staff(cls):
    staffers = cls.all().filter('type IN', ['StaffKey', 'StaffNoKey']).filter('active =', True).order('-created')
    # Auto-signout
    for staffer in staffers.fetch(1000):
      td = datetime.now()-staffer.created
      if td.seconds > MAX_SIGNIN_TIME:
        staffer.active = False
        staffer.closed = datetime.now()
        staffer.time_delta = MAX_SIGNIN_TIME
        staffer.put()
        mail.send_mail(
            sender="Signin Machine <signin@hackerdojo.com>",
            to=staffer.email,
            subject="Are you still staffing the Dojo?",
            body="You were automatically signed out after "+ str(MAX_SIGNIN_TIME/60/60) + " hours.\n\n"+
                 "You can always sign-in again at http://hackerdojo-signin.appspot.com/ if you are still here.\n\n")
    return staffers
  
  @classmethod
  def deactivate_staffer(cls, email):
    staffer = cls.get_active_staff().filter('email =', email).get()
    staffer.active = False
    staffer.closed = datetime.now()
    td = datetime.now()-staffer.created
    staffer.time_delta = (td.days*86400)+td.seconds
    staffer.put()
  
  def name_or_nick(self):
    return self.name or self.email.split('@')[0]

  @classmethod
  def signin(cls, email, type):
    if not '@' in email:
      raise EmailError("malformed e-mail")
    hash = hashlib.md5(email).hexdigest()
    image = 'http://0.gravatar.com/avatar/%s' % hash
    name = string.capwords(email.split('@')[0].replace('.', ' '))
    # prevents double signin...
    previous_signin = db.GqlQuery("SELECT * FROM Signin WHERE email = '%s' AND active = true" % email).get()
    if previous_signin:
      try:
        cls.deactivate_staffer(email)
      except:
        logging.info("Failed deactivating old Signin object.")
    s = Signin(email=email, type=type, image_url=image, name=name)
    DailyCount.increment_and_get()    
    s.put()
    if "mark.hutsell" in email or "some.other.evilguy" in email:
        mail.send_mail(sender="Signin Machine <signin@hackerdojo.com>", to="Emergency Paging System <page@hackerdojo.com>",
           subject="Sign-in: " + email, body="Sign in")
        urlfetch.fetch("http://www.dustball.com/call/call.php?str=Sign+in+"+email)
    return s

# Unlike the signin log, this table is one row per e-mail address.
class SigninRecord(db.Model):
  email = db.StringProperty(required=True)
  first_signin = db.DateTimeProperty(auto_now_add=True)
  last_signin = db.DateTimeProperty()
  signins = db.IntegerProperty()
  
  @classmethod
  def signin(cls, email, when):
    rec = cls.all().filter('email =', email).get()
    if rec:
      rec.signins += 1
      rec.last_signin = when
    else:
      rec = SigninRecord(email=email, first_signin=when, last_signin=when, signins=1)
    rec.put()
    return rec

# AJAX Signin
class SigninHandler(webapp.RequestHandler):
  def get(self):
    email = self.request.get('email')
    # time.sleep(2)
    type = self.request.get('type')
    if email and type:
      signin = Signin.signin(email, type)
      record = SigninRecord.signin(email, datetime.now())
      tos = False
      if record.signins == 1:
        tos = True
      # PSUEDO CODE: if record.last_signin < date of last TOS change
      # PSUEDO CODE:   tos = True
      response = {"signins":record.signins, "name":signin.name, "tos":tos}
    else:
      response = {"error": "need to specify email and type"}
    current_event = Event.get_current_event()
    if current_event and datetime.now()>current_event.from_time and datetime.now() < current_event.to_time:
      urlfetch.fetch(url=current_event.webhook_url,
                        payload=self.request.query_string,
                        method=urlfetch.POST,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'})
      
    self.response.out.write(json.dumps(response))

# Initializes SigninRecord database (see util.py)
class InitRecordsHandler(webapp.RequestHandler):
  def get(self):
    deferred.defer(util.init_records)
    self.response.out.write("Done\n")

# Count number of singins, useful for debugging
class CountHandler(webapp.RequestHandler):
  def get(self):
    i = 0
    for s in SigninRecord.all():
      i = i + s.signins
    self.response.out.write(str(i))
  
# Exports e-mail addresses (usually disabled)
class ExportHandler(webapp.RequestHandler):
  def get(self):
    for e in SigninRecord.all():
      self.response.out.write(e.email+"\n")

# Renders the main page      
class CCHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/cc.html', locals()))
  

# Renders the main page      
class MainHandler(webapp.RequestHandler):
  def get(self):
    today_count = DailyCount.get()
    if today_count > 1:
      today_count_signigicant = True
    dayofWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    oldDate = datetime.now(Pacific())
    day = dayofWeek[datetime.weekday(oldDate)]
    event = Event.get_current_event()
    if event and datetime.now()>event.from_time and datetime.now() < event.to_time:
      current_event = event
    self.response.out.write(template.render('templates/main.html', locals()))
  
  def post(self):
    email = self.request.get('email')
    type = self.request.get('type')
    Signin.signin(email, type)
    self.redirect('/')

# Used by the kiosk in an iframe
class StaffHandler(webapp.RequestHandler):
  def get(self):
    staff = Signin.get_active_staff()
    self.response.out.write(template.render('templates/staff.html', locals()))
  
  def post(self):
    email = self.request.get('email')
    if email:
      Signin.deactivate_staffer(email)
    self.redirect('/staff')

# Used by /log - the user facing log of people that have signed in last 12 hours
class LogHandler(webapp.RequestHandler):
  def get(self):
    staff_db = db.GqlQuery("SELECT * FROM Signin WHERE created >= DATETIME(:earlier_this_morning) ORDER BY created desc LIMIT 500",
      earlier_this_morning=(datetime.now(Pacific()).strftime("%Y-%m-%d 00:00:00")))
    staff = []
    for s in staff_db:
      if s.type in ["Anonymous","Guest","Event"]:
        s.name = ""
        s.anonymous = True
      if s.type in ["StaffKey","StaffNoKey"]:
        s.type = "Staff"
      if s.type in ["Event"]:
        s.type = "Event Guest"
      staff.append(s)
    self.response.out.write(template.render('templates/log.html', locals()))

# Used by the widget on the dojo website
class MiniStaffHandler(webapp.RequestHandler):
  def get(self):
    staff = Signin.get_active_staff()
    isopen = staff.count() > 0
    self.response.out.write(template.render('templates/ministaff.html', locals()))

# Sends out an e-mail to members every Sunday
class AppreciationEmailHandler(webapp.RequestHandler):
  def get(self):
    staff_members = db.GqlQuery("SELECT * FROM Signin WHERE created >= DATETIME(:start) AND type IN :types ",
      start=(datetime.now(Pacific())-timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),types=['StaffKey','StaffNoKey'])
    content = """To Dojo Members:\n\nThanks for helping run the dojo last week!  Our heros included:\n\n""" % locals()
    totals = {}
    emails = []
    for staff_member in staff_members:
      staff_member.name = string.capwords(staff_member.name)
      if staff_member.time_delta:
        emails.append(staff_member.email)
        if staff_member.time_delta > MAX_SIGNIN_TIME:
          staff_member.time_delta = MAX_SIGNIN_TIME
        if staff_member.name in totals.keys():
          totals[staff_member.name] = totals[staff_member.name]+staff_member.time_delta
        else:
          totals[staff_member.name] = staff_member.time_delta
    for total in sorted(totals.keys()):
      if(totals[total] > 0):
        content = content + " - " + total + ": " + str(math.floor(float(totals[total])/360)/10 ) + " hours\n"
      else:
        pass
    content = content + """\nThanks,\nEveryone at the Dojo"""
    if self.request.get('sendemail'):
      weekof = (datetime.now(Pacific())-timedelta(days=7)).strftime("%b %e")
      mail.send_mail(sender="Signin Machine <signin@hackerdojo.com>",
                  to="announcements@hackerdojo.com",
                  subject="Hacker Dojo Member Appreciation - Week of " + weekof,
                  body=content)
    self.response.out.write(content)

# Used by /open, for example by the Twilio phone number ("The Dojo is open, staffed by x,y,z..")
class OpenHandler(webapp.RequestHandler):
  def get(self):
    staff = Signin.get_active_staff()
    count = staff.count(1000)
    if count > 0:
      staff = [s.name_or_nick().split(' ')[0] for s in staff.fetch(1000)]
      if count > 1:
        last_staff = staff.pop()
        self.response.out.write("Hacker Dojo is currently open, staffed by %s and %s." % (', '.join(staff), last_staff))
      else:
        self.response.out.write("Hacker Dojo is currently open, staffed by our hero, %s." % staff[0])
    else:
      self.response.out.write("Hacker Dojo is unfortunately closed.")

# Used by /stats
class StatHandler(webapp.RequestHandler):
  def get(self):
    self.response.out.write(template.render('templates/stats.html', locals()))

# Used by /report/donations
class DonationReportHandler(webapp.RequestHandler):
  def get(self):
    donations = Donation.all().order("-amount")
    total = 0
    for d in donations:
      if d.status_code == 1 and int(d.transaction_id) > 0:
        total += d.amount
    self.response.out.write(template.render('templates/donations.html', locals()))


# Used by /report/doorlog
class DoorLogReportHandler(webapp.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url('/report/doorlog'))
    if users.is_current_user_admin():
      logs = DoorLog.all().order("-event_time").fetch(500)
      self.response.out.write(template.render('templates/doorlog.html', locals()))
    else:
      self.response.out.write("Sorry, need admin access")


#class SigninRecord(db.Model):
#  email = db.StringProperty(required=True)
#  first_signin = db.DateTimeProperty(auto_now_add=True)
#  last_signin = db.DateTimeProperty()
#  signins = db.IntegerProperty()
#

class RecentActiveHandler(webapp.RequestHandler):
  def get(self):
    for signin in SigninRecord.all().order("-signins"):
      if "2013-02" in str(signin.last_signin) and signin.signins>1:
        self.response.out.write(signin.email)
        self.response.out.write(",")
        self.response.out.write(signin.signins)
        self.response.out.write(",")
        self.response.out.write(signin.last_signin)
        self.response.out.write("<br/>")

# Used by /stats/*
class StatsHandler(webapp.RequestHandler):
  def get(self,format):
    days = {}
    formats = {'daily':"%Y-%m-%d", 'weekly':"%Y Week %U", 'monthly':"%Y-%m"}
    date_format = formats[format]
    interested = ['Guest','Anonymous','Staff','Member','Event']
    self.response.headers.add_header('Content-Type',"text/csv")
    self.response.headers.add_header('Content-disposition',"attachment;filename=signin-stats-"+format+".csv")
    self.response.out.write("Date")
    for t in interested:
        self.response.out.write(",")
        self.response.out.write(t)
    self.response.out.write("\n")
    
    for signin in Signin.all().order("created"):
      ts = string.replace(signin.created.strftime(date_format),"Week 00","Week 01")
      if ts not in days:
        days[ts] = {}
      if signin.type in ['StaffKey','StaffNoKey']:
        signin.type = 'Staff'
      if signin.type not in days[ts]:
        days[ts][signin.type] = 0
      days[ts][signin.type] += 1
      if days[ts][signin.type] == 1401:
        days[ts][signin.type] = 14

    ordered_days = days.keys()
    ordered_days.sort()
    
    for day in ordered_days:
      self.response.out.write(day)
      for t in interested:
        self.response.out.write(",")
        if t in days[day]:
          self.response.out.write(days[day][t])
        else:
          self.response.out.write("0")
      self.response.out.write("\n")

class DoorLogHandler(webapp.RequestHandler):
    def get(self):
        if self.request.get('door') and self.request.get('status'):
          dl = DoorLog(
            username = self.request.get('username'),
            status = self.request.get('status'),
            rfid_tag = self.request.get('rfid_tag'),
            door = self.request.get('door')
            )
          dl.put()
          self.response.out.write(json.dumps({"result": "ok"}))
        else:
          self.response.out.write(json.dumps({"error": "must specify 'door' and 'status' parameters"}))

class ChargeHandler(webapp.RequestHandler):
    def post(self):
        first_name = self.request.get('first_name')
        last_name = self.request.get('last_name')
        card = CreditCard(
                          number = self.request.get('cc'),
                          month = self.request.get('month'),
                          year = "20"+self.request.get('year'),
                          first_name = first_name,
                          last_name = last_name,
                          code = ''    
                          )
        name = first_name + " " + last_name
        gateway = AimGateway(auth_net_login_id, auth_net_trans_key)
        gateway.use_test_mode = False
        gateway.use_test_url = False
        if "KLUG" in last_name:
          gateway.use_test_mode = True
        amount = float(int(random.random()*2000))/100
        dollar_amount = '$%.2f' % amount
        response = gateway.sale(amount, card)
        d = Donation(amount=amount, transaction_id=response.trans_id, status=response.status_strings[response.status], status_code=response.status, name=name)
        d.put()
        self.response.out.write(json.dumps({"trans_id": response.trans_id, 
                                                  "amount": amount,
                                                  "dollar_amount": dollar_amount,
                                                  "status": response.status_strings[response.status], 
                                                  "status_code": response.status,
                                                  "message": response.message}))

# Used by /staffjson (not sure what uses it)
class JSONHandler(webapp.RequestHandler):
  def get(self):
    staff = Signin.get_active_staff()
    
    def to_dict(staffer):
        return dict(
            name=staffer.name_or_nick(),
            email=staffer.email,
            image_url=staffer.image_url,
            type=staffer.type,
            created=staffer.created.strftime("%m-%d-%Y %H:%M:%S"),
            refTime=datetime.now().strftime("%m-%d-%Y %H:%M:%S"),)
            
    self.response.out.write(wjson.dumps([to_dict(staffer) for staffer in staff]))

# Used to power there@hackerdojo.com - send e-mail to everyone "there" (signed in) at the Dojo
class MailHandler(InboundMailHandler):
    def receive(self, mail_message):
        
        staff = Signin.get_active_staff()
        count = staff.count(1000)
        if count > 0:
          staff = [s.email for s in staff.fetch(1000)]
          mail.send_mail(
              sender="Signin Machine <signin@hackerdojo.com>",
              to=(', '.join(staff)),
              cc=mail_message.sender,
              subject="[there@] " + mail_message.subject,
              body=mail_message.body,
              reply_to=mail_message.sender
              )
        else:
          mail.send_mail(
            sender="Signin Machine <signin@hackerdojo.com>",
            to=mail_message.sender,
            subject="there@ bounce message",
            body="Sorry, it doesn't look like anyone is signed in as staff right now.")

app = webapp.WSGIApplication([
        ('/', MainHandler), 
        ('/cc', CCHandler), 
        (r'^/_ah/mail/there.*', MailHandler),
    ('/eventmode', EventModeHandler),
    ('/report/donations', DonationReportHandler),
    ('/report/recentactive', RecentActiveHandler),
    ('/report/doorlog', DoorLogReportHandler),
    ('/ministaff', MiniStaffHandler),
    ('/signin', SigninHandler),
    ('/staff', StaffHandler),                
    ('/api/doorlog', DoorLogHandler),                
    ('/api/charge', ChargeHandler),                
    ('/sstats/?', StatHandler),
    ('/sstats/(.+)', StatsHandler),
    ('/log', LogHandler),
    # ('/initrecords', InitRecordsHandler), 
    ('/count', CountHandler), 
    # ('/export', ExportHandler), 
    ('/appreciationemail', AppreciationEmailHandler),
        ('/staffjson', JSONHandler),
        ], debug=True)
  
