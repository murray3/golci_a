from datetime import datetime
from lib import functions
from google.appengine.ext import ndb 
from google.appengine.ext.ndb import model
from ndb import Key

class Ari_types(ndb.model):
    ari = ndb.StringProperty()
    description = ndb.StringProperty()     

a =  Ari_types()
a.ari = "Ad Hominem"
a.description = "Against the Person"
a.put()

#from google.appengine.ext import db
class Branch(ndb.model):
    branch = ndb.StringProperty()
    description = ndb.StringProperty()

b = Branch()
b.branch = "Business"
b.description ="Business"
b.put()
b = Branch()
b.branch = "Entertainment"
b.description = "Entertainment"
b.put()
b = Branch()
b.branch = "Economics"
b.description = "Economics"
b.put()
b = Branch()
b.branch = "Politics"
b.description = "Politics"
b.put()

