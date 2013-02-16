# Copy this file into secrets.py and set keys, secrets and scopes.
__author__ = 'Chris Murray - cjjmurray@gmail.com'
__website__ = 'www.golci.com'
# This is a session secret key used by webapp2 framework.
# Get 'a random and long string' from here: 
# http://clsc.net/tools/random-string-generator.php
# or execute this from a python shell: import os; os.urandom(64)
SESSION_KEY = "9545a8p41gskab7wx6j84h9bx1wxo71j12789047z0889zlld"

# Google APIs
GOOGLE_APP_ID = '758539385801-g9gim29g84bpp8f6if3jcr3jnjeg2ind.apps.googleusercontent.com'
GOOGLE_APP_SECRET = 'naOI2BWEl4uj3EXscP7rqmGm'

# Facebook auth apis
FACEBOOK_APP_ID = 'app id'
FACEBOOK_APP_SECRET = 'app secret'

# https://www.linkedin.com/secure/developer
LINKEDIN_CONSUMER_KEY = 'consumer key'
LINKEDIN_CONSUMER_SECRET = 'consumer secret'

# https://manage.dev.live.com/AddApplication.aspx
# https://manage.dev.live.com/Applications/Index
WL_CLIENT_ID = 'client id'
WL_CLIENT_SECRET = 'client secret'

# https://dev.twitter.com/apps
TWITTER_CONSUMER_KEY = 'oauth1.0a consumer key'
TWITTER_CONSUMER_SECRET = 'oauth1.0a consumer secret'

# config that summarizes the above
AUTH_CONFIG = {
  'google'      : (GOOGLE_APP_ID,         GOOGLE_APP_SECRET,        'https://www.googleapis.com/auth/userinfo.profile'),
  'facebook'    : (FACEBOOK_APP_ID,       FACEBOOK_APP_SECRET,      'user_about_me'),
  'windows_live': (WL_CLIENT_ID,          WL_CLIENT_SECRET,         'wl.signin'),
  'twitter'     : (TWITTER_CONSUMER_KEY,  TWITTER_CONSUMER_SECRET),
  'linkedin'    : (LINKEDIN_CONSUMER_KEY, LINKEDIN_CONSUMER_SECRET),
}
