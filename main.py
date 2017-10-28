import hashlib
import json
import logging
import string
import urllib
from datetime import datetime

from google.appengine.api import channel
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import deferred
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

import util
from util import Pacific

# disabled to disable credit card processing
# if you want to re-enable it, get the info and don't put it on github
# from keys import auth_net_login_id, auth_net_trans_key

MAX_SIGNIN_TIME = 60 * 60 * 8


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
            count_rec = DailyCount(day=datetime.now(Pacific()).date(), count=1)
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
    def signin(cls, email, type):
        if not '@' in email:
            raise EmailError("malformed e-mail")
        hash = hashlib.md5(email).hexdigest()
        image = 'https://0.gravatar.com/avatar/%s' % hash
        name = string.capwords(email.split('@')[0].replace('.', ' '))
        # if sign in with email for today already there do nothing
        # TODO: prevent double signin
        s = Signin(email=email, type=type, image_url=image, name=name)
        DailyCount.increment_and_get()
        s.put()
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
        for ch in (range(1, 3)):
            channel.send_message("CH" + str(ch), json.dumps(
                {"email": email, "first": str(rec.first_signin), "last": str(rec.last_signin), "count": rec.signins}))
        return rec


# AJAX Signin
class SigninHandler(webapp.RequestHandler):
    def get(self):
        email = self.request.get('email')
        # time.sleep(2)
        type = self.request.get('type')

        if email and type:
            # Perform an API request for the signup application.
            response = {}
            if type == "Member":
                base_url = "https://hd-signup-hrd.appspot.com/api/v1/signin"
                query_str = urllib.urlencode({"email": email})
                result = urlfetch.fetch(base_url, method=urlfetch.POST,
                                        payload=query_str, follow_redirects=False)
                logging.info("Got response from signup app: %s" % (result.content))

                if result.status_code != 200:
                    error_json = json.loads(result.content)
                    if error_json["type"] == "InvalidEmailException":
                        logging.debug("User %s is not an active member." % (email))
                        response["nomember"] = True
                        self.response.out.write(json.dumps(response))
                        return
                    response["nomember"] = False

                    self.response.set_status(500)
                    response = {"error_message": "Backend API call failed."}
                    self.response.out.write(json.dumps(response))
                    return

                member_json = json.loads(result.content)
                if member_json["visits_remaining"] == 0:
                    # No more visits left this month.
                    logging.debug("User %s needs to upgrade." % (email))
                    response["status"] = "upgrade"
                else:
                    response["status"] = "normal"
                    response["visits_remaining"] = member_json["visits_remaining"]
            else:
                response["status"] = "normal"

            signin = Signin.signin(email, type)
            record = SigninRecord.signin(email, datetime.now())
            tos = False
            if record.signins == 1 and "hackerdojo.com" not in email:
                tos = True
            # PSUEDO CODE: if record.last_signin < date of last TOS change
            # PSUEDO CODE:   tos = True

            response["signins"] = record.signins
            response["name"] = signin.name
            response["tos"] = tos
        else:
            response = {"error_message": "need to specify email and type"}

        self.response.out.write(json.dumps(response))


# Initializes SigninRecord database (see util.py)
class InitRecordsHandler(webapp.RequestHandler):
    def get(self):
        deferred.defer(util.init_records)
        self.response.out.write("Done\n")


# Exports e-mail addresses (usually disabled)
class ExportHandler(webapp.RequestHandler):
    def get(self):
        for e in SigninRecord.all():
            self.response.out.write(e.email + "\n")


# Renders the main page
class MainHandler(webapp.RequestHandler):
    def get(self):
        # This is running on shared computers, so we don't want to leave anybody
        # logged in.
        if users.get_current_user():
            logging.info("Logging out current user.")
            self.redirect(users.create_logout_url(self.request.uri))
            return

        today_count = DailyCount.get()
        if today_count > 1:
            today_count_significant = True
        dayofWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        oldDate = datetime.now(Pacific())
        day = dayofWeek[datetime.weekday(oldDate)]
        # event = Event.get_current_event()
        self.response.out.write(template.render('templates/main.html', locals()))

    def post(self):
        email = self.request.get('email')
        type = self.request.get('type')
        Signin.signin(email, type)
        self.redirect('/')


# Used by /log - the user facing log of people that have signed in last 12 hours
class LogHandler(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if not user:
            self.redirect(users.create_login_url('/log'))
        staff_db = db.GqlQuery(
            "SELECT * FROM Signin WHERE created >= DATETIME(:earlier_this_morning) ORDER BY created desc LIMIT 500",
            earlier_this_morning=(datetime.now(Pacific()).strftime("%Y-%m-%d 00:00:00")))
        staff = []
        for s in staff_db:
            if s.type in ["Anonymous", "Guest", "Event"]:
                s.name = ""
                s.anonymous = True
            if s.type in ["StaffKey", "StaffNoKey"]:
                s.type = "Staff"
            if s.type in ["Event"]:
                s.type = "Event Guest"
            staff.append(s)
        self.response.out.write(template.render('templates/log.html', locals()))


# Sends out an e-mail to members every Sunday
# class AppreciationEmailHandler(webapp.RequestHandler):
#     def get(self):
#         staff_members = db.GqlQuery("SELECT * FROM Signin WHERE created >= DATETIME(:start) AND type IN :types ",
#                                     start=(datetime.now(Pacific()) - timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S"),
#                                     types=['StaffKey', 'StaffNoKey'])
#         content = """To Dojo Members:\n\nThanks for helping run the dojo last week!  Our heros included:\n\n""" % locals()
#         totals = {}
#         emails = []
#         for staff_member in staff_members:
#             staff_member.name = string.capwords(staff_member.name)
#             if staff_member.time_delta:
#                 emails.append(staff_member.email)
#                 if staff_member.time_delta > MAX_SIGNIN_TIME:
#                     staff_member.time_delta = MAX_SIGNIN_TIME
#                 if staff_member.name in totals.keys():
#                     totals[staff_member.name] = totals[staff_member.name] + staff_member.time_delta
#                 else:
#                     totals[staff_member.name] = staff_member.time_delta
#         for total in sorted(totals.keys()):
#             if (totals[total] > 0):
#                 content = content + " - " + total + ": " + str(math.floor(float(totals[total]) / 360) / 10) + " hours\n"
#             else:
#                 pass
#         content = content + """\nThanks,\nEveryone at the Dojo"""
#         if self.request.get('sendemail'):
#             weekof = (datetime.now(Pacific()) - timedelta(days=7)).strftime("%b %e")
#             mail.send_mail(sender="Signin Machine <signin@hackerdojo.com>",
#                            to="announcements@hackerdojo.com",
#                            subject="Hacker Dojo Member Appreciation - Week of " + weekof,
#                            body=content)
#         self.response.out.write(content)


# Used to power there@hackerdojo.com - send e-mail to everyone "there" (signed in) at the Dojo
# class MailHandler(InboundMailHandler):
#    def receive(self, mail_message):
#        staff = Signin.get_active_staff()
#        count = staff.count(1000)
#        if count > 0:
#          staff = [s.email for s in staff.fetch(1000)]
#          mail.send_mail(
#              sender="Signin Machine <signin@hackerdojo.com>",
#              to=(', '.join(staff)),
#              cc=mail_message.sender,
#              subject="[there@] " + mail_message.subject,
#              body=mail_message.body,
#              reply_to=mail_message.sender
#              )
#        else:
#          mail.send_mail(
#            sender="Signin Machine <signin@hackerdojo.com>",
#            to=mail_message.sender,
#            subject="there@ bounce message",
#            body="Sorry, it doesn't look like anyone is signed in as staff right now.")


""" Handler for making RFID API call to signup app. """


class RfidApiHandler(webapp.RequestHandler):
    """ key: The RFID key of the user. """

    def get(self, key):
        base_url = "https://hd-signup-hrd.appspot.com/api/v1/rfid"
        query_str = urllib.urlencode({"id": key})
        response = urlfetch.fetch(base_url, method=urlfetch.POST,
                                  payload=query_str, follow_redirects=False)
        logging.info("Got response from API: %s" % (response.content))

        to_send = {}
        if response.status_code != 200:
            error = json.loads(response.content)
            if error["type"] == "InvalidKeyException":
                # It signed in a bad key.
                to_send["bad_key"] = True
                self.response.out.write(json.dumps(to_send))
                return
            to_send["bad_key"] = False

            self.response.set_status(500)
            to_send = {"error": "Backend API request failed."}

        # handle_current_event(self)

        user_info = json.loads(response.content)

        signin = Signin.signin(user_info["email"], "Member")
        record = SigninRecord.signin(user_info["email"], datetime.now())

        if user_info["visits_remaining"] == 0:
            logging.debug("User %s needs to upgrade." % (user_info["name"]))
            to_send["status"] = "upgrade"
        else:
            to_send["status"] = "normal"
            to_send["visits_remaining"] = user_info["visits_remaining"]

        to_send["gravatar"] = user_info["gravatar"]
        to_send["name"] = user_info["name"]
        to_send["username"] = user_info["username"]
        to_send["auto_signin"] = user_info["auto_signin"]
        to_send["signins"] = record.signins

        self.response.out.write(json.dumps(to_send))


app = webapp.WSGIApplication([
    ('/', MainHandler),
    ('/rfid/(.+)', RfidApiHandler),
    ('/signin', SigninHandler),
    ('/log', LogHandler),
    # ('/initrecords', InitRecordsHandler),
    # ('/export', ExportHandler),
    # ('/appreciationemail', AppreciationEmailHandler),

], debug=True)
