class Branch(db.Model):
    branch = db.StringProperty()
    description = db.StringProperty()

class Contention(db.Model):
    # Basic info.
    author = db.StringProperty()
    author_id = db.IntegerProperty()
   # author_golci = db.ReferenceProperty(User,
   #                            collection_name='golci')
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now_add=True)
    branch_key = db.ReferenceProperty(Branch,
                               collection_name='contentions')
    branch_name = db.StringProperty()
    draft = db.BooleanProperty(default=True)
    g_frames = db.IntegerProperty()
    text = db.StringProperty()
    description = db.StringProperty()
    step_count = db.IntegerProperty()
    #tags = db.StringListProperty()
    #blob = blobstore.BlobReferenceProperty(required=True)
    image_URL = db.StringProperty()
    image = db.BlobProperty()
    image_1 = db.BlobProperty()
    image_2 = db.BlobProperty()
    image_3 = db.BlobProperty()
    image_4 = db.BlobProperty()

import json

from datetime import datetime
from lib import functions
from google.appengine.ext import db
from google.appengine.api import urlfetch


def clone_entity(e, skip_auto_now=False, skip_auto_now_add=False, **extra_args):
  """Clones an entity, adding or overriding constructor attributes.

  The cloned entity will have exactly the same property values as the original
  entity, except where overridden. By default it will have no parent entity or
  key name, unless supplied.

  Args:
    e: The entity to clone
    skip_auto_now: If True then all DateTimeProperty propertes will be skipped which have the 'auto_now' flag set to True
    skip_auto_now_add: If True then all DateTimeProperty propertes will be skipped which have the 'auto_now_add' flag set to True
    extra_args: Keyword arguments to override from the cloned entity and pass
      to the constructor.
  Returns:
    A cloned, possibly modified, copy of entity e.
  """

  klass = e.__class__
  props = {}
  for k, v in klass.properties().iteritems():
    if not (type(v) == db.DateTimeProperty and ((skip_auto_now and getattr(v, 'auto_now')) or (skip_auto_now_add and getattr(v, 'auto_now_add')))):
      if type(v) == db.ReferenceProperty:
        value = getattr(klass, k).get_value_for_datastore(e)
      else:
        value = v.__get__(e, klass)
      props[k] = value
  props.update(extra_args)
  print(extra_args)
  print(props)
  return klass(**props)

c = Contention()
c.content = "test process"
c.branch_name = "Economics"
c.author = "test auth"
c.put()
argo={'content': 'test2','author': 'test auth2','branch_name': 'Business'}
dd = clone_entity(c,content='test2',author='test auth2',branch_name='Business')
dd.put()
