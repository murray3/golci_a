
__author__ = 'Rodrigo Augosto (@coto) - contact@protoboard.cl'
__website__ = 'www.protoboard.cl'
from google.appengine.ext import blobstore
from webapp2_extras.appengine.auth.models import User
from google.appengine.ext.ndb import model
from google.appengine.ext import db
# based on https://gist.github.com/kylefinley
class User(User):
    """
    Universal user model. Can be used with App Engine's default users API,
    own auth or third party authentication methods (OpenId, OAuth etc).
    """
    #: Creation date.
    created = model.DateTimeProperty(auto_now_add=True)
    #: Modification date.
    updated = model.DateTimeProperty(auto_now=True)
    #: User defined unique name, also used as key_name.
    username = model.StringProperty(required=True)
    #: User Name
    name = model.StringProperty()
    #: User Last Name
    last_name = model.StringProperty()
    #: User email
    email = model.StringProperty(required=True)
    #: Password, only set for own authentication.
    password = model.StringProperty(required=True)
    #: User Country
    country = model.StringProperty()
    #: User Date of Birth
    date_of_birth = model.DateProperty()

    #: Authentication identifier according to the auth method in use. Examples:
    #: * own|username
    #: * db|user_id
    #: * openid|identifier
    #: * twitter|username
    #: * facebook|username
    auth_id = model.StringProperty(repeated=True)
#    auth_id = model.StringProperty()
    # Flag to persist the auth across sessions for third party auth.
    auth_remember = model.BooleanProperty(default=False)

# TODO: use these methods for authentication and reset password
#    @classmethod
#    def get_by_username(cls, username):
#        return cls.query(cls.username == username).get()
#
#    @classmethod
#    def get_by_auth_id(cls, auth_id):
#        return cls.query(cls.auth_id == auth_id).get()
#

class Branch(db.Model):
    branch = db.StringProperty()
    description = db.StringProperty()

class Tag(db.Model):
    tag = db.StringProperty()	
    
class Golci(db.Model):
    # Basic info.
    #author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now_add=True)    
     
class Contention(db.Model):
    # Basic info.
    author = db.StringProperty()
    author_img = db.StringProperty()
    author_id = db.IntegerProperty()
   # author_golci = db.ReferenceProperty(User,
   #                            collection_name='golci')
    content = db.StringProperty(multiline=True)
    date = db.DateTimeProperty(auto_now_add=True)
    branch_key = db.ReferenceProperty(Branch,
                               collection_name='contentions')
    branch_name = db.StringProperty()
    draft = db.BooleanProperty(default=True)
    g_frames = db.IntegerProperty(default=1)
    text = db.StringProperty()
    description = db.StringProperty()
    step_count = db.IntegerProperty()
    #tags = db.StringListProperty()
    #blob = blobstore.BlobReferenceProperty(required=True)
    image_id = db.IntegerProperty()
    image = db.BlobProperty()

    
def ancestor_list_validator(l):
    if len(l) != len(set(l)):
        raise Exception("Repeated values in ancestor list!")

class Images(db.Model):
    contention_key = db.ReferenceProperty(Contention,
                               collection_name='images')
    author = db.StringProperty()
    author_id = db.IntegerProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    parent_id = db.IntegerProperty()
    element_type = db.StringProperty()
    decription = db.StringProperty()
    image = db.BlobProperty()
     
class Elements(db.Model):
    contention_key = db.ReferenceProperty(Contention,
                               collection_name='elements')
    elements_tree = db.StringProperty()
    top_level = db.IntegerProperty()  
    g_frame = db.IntegerProperty()
    pending = db.BooleanProperty(default=False)   
    element_keys = db.ListProperty(db.Key, validator=ancestor_list_validator)
    element_type = db.StringProperty(
        choices=('contention', 'reason', 'objection', 'rebuttal', 'support'))
    author = db.StringProperty()
    author_img = db.StringProperty()
    author_id = db.IntegerProperty()
    branch_name = db.StringProperty()
    content = db.StringProperty(multiline=True)
    rabbit_rule_text = db.StringProperty() 
    holdhands_rule_text = db.StringProperty()
    date = db.DateTimeProperty(auto_now_add=True)
    parent_id = db.IntegerProperty()
    parent_t = db.StringProperty()
    image_id = db.IntegerProperty()
    image = db.BlobProperty()
    image_1 = db.StringProperty()
    image_blob_1 = db.BlobProperty()
    image_2 = db.StringProperty()
    image_blob_2 = db.BlobProperty()
    image_3 = db.StringProperty()
    image_blob_3 = db.BlobProperty()
    image_4 = db.StringProperty()
    image_blob_4 = db.BlobProperty()

class Ari_types(db.Model):
    ari = db.StringProperty()
    description = db.StringProperty()    
    date = db.DateProperty()   
    image_URL = db.StringProperty()
    image = db.StringProperty()     
    
    
class Ari(db.Model):
    contention_key = db.ReferenceProperty(Contention,
                               collection_name='ari')
    ari_type_key = db.ReferenceProperty(Ari_types,
                               collection_name='ari_type')
                               
    #author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    element_id  = db.StringProperty()
    type  = db.StringProperty()    
    date = db.DateProperty()   
    image_URL = db.StringProperty()
    image = db.StringProperty()    
    
class golci_link(db.Model):
    element_key = db.ReferenceProperty(Elements,
                               collection_name='element')
    #author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    description = db.StringProperty()    
    date = db.DateProperty()   
    image_URL = db.StringProperty()
    image = db.StringProperty()
    
class golci_history(db.Model):
    contention_key = db.ReferenceProperty(Contention,
                               collection_name='history')
    parent_id = db.StringProperty()
    #author = db.UserProperty()
    content = db.StringProperty(multiline=True)
    description = db.StringProperty()    
    date = db.DateTimeProperty(auto_now_add=True)
    step = db.IntegerProperty()    
    image_URL = db.StringProperty()
    image = db.StringProperty()