import logging, email

# This function recreates the SigninRecord table from scratch
# (May never need to be used again)
def init_records():
  import main
  logging.info("Wiping old SigninRecord table.")
  for s in main.SigninRecord.all():
    s.delete()
  logging.info("Scanning signin table.")
  count = {}
  first = {}
  last = {}
  for signin in main.Signin.all().order("created"):
     if signin.email not in first:
       first[signin.email] = signin.created  
     if signin.email not in count:
       count[signin.email] = 1
     else:
       count[signin.email] += 1
     last[signin.email] = signin.created
  logging.info("Populating SigninRecord table.")
  for email in count:
    main.SigninRecord(email=email, first_signin = first[email], last_signin=last[email], signins = count[email]).put()
  logging.info("Done.")
