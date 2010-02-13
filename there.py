import logging, email
from google.appengine.ext import webapp 
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler 
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.api import mail

class MailHandler(InboundMailHandler):
    def receive(self, mail_message):
        logging.info("Received a message from: " + mail_message.sender)
        
        mail.send_mail(
              sender=mail_message.sender,
              to="brian.klug@gmail.com",
              subject=mail_message.subject,
              body=mail_message.body)

application = webapp.WSGIApplication([
  MailHandler.mapping()
], debug=True)
def main():
  run_wsgi_app(application)
if __name__ == "__main__":
  main()