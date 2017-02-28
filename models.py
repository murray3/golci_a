# -*- coding: utf-8 -*-
__author__ = 'Chris Murray - cjjmurray@gmail.com'
__website__ = 'www.golci.com'
from google.appengine.ext import blobstore
from google.appengine.ext import ndb 
from google.appengine.api import images
from webapp2_extras.appengine.auth.models import User as golciUser

class GGroup(ndb.Model):
    group_name = ndb.StringProperty()
    group_desc = ndb.StringProperty()
    owner_id = ndb.IntegerProperty()
	
class GGroup_Users(ndb.Model):
    user_id = ndb.IntegerProperty()
    date_joined = ndb.DateTimeProperty(auto_now_add=True)
    active = ndb.BooleanProperty(default=True)
    date_leave = ndb.DateTimeProperty()
    group_key = ndb.KeyProperty(kind=GGroup, repeated=True)

class Branch(ndb.Model):
    branch = ndb.StringProperty()
    description = ndb.StringProperty()

class Tags(ndb.Model):
    tag = ndb.StringProperty()	
    
class Golci(ndb.Model):
    # Basic info.
    #author = db.UserProperty()
    content = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)    
	
class Elements(ndb.Model):
    element_id = ndb.StringProperty()
    g_frame = ndb.IntegerProperty()
    pending = ndb.BooleanProperty(default=False)   
    element_type = ndb.StringProperty(
        choices=('contention', 'reason', 'objection', 'rebuttal', 'support'))
    author = ndb.StringProperty()
    author_img = ndb.StringProperty()
    author_id = ndb.IntegerProperty()
    content = ndb.StringProperty()
    sure_score = ndb.IntegerProperty(default=1)
    sentence_rule = ndb.IntegerProperty()
    rabbit_rule = ndb.IntegerProperty() 
    holdhands_rule = ndb.IntegerProperty() 
    rabbit_rule_text = ndb.StringProperty() 
    holdhands_rule_text = ndb.StringProperty()
    date = ndb.DateTimeProperty(auto_now_add=True)
    other_date = ndb.StringProperty()
    parent_id = ndb.StringProperty()
    parent_t = ndb.StringProperty()
    num_images = ndb.IntegerProperty(default=0)
    image1 = ndb.BlobKeyProperty()
    image_1_url = ndb.StringProperty()
    image2 = ndb.BlobKeyProperty()
    image_2_url = ndb.StringProperty()
    image3 = ndb.BlobKeyProperty()
    image_3_url = ndb.StringProperty()
    image4 = ndb.BlobKeyProperty()
    image_4_url = ndb.StringProperty()
    image5 = ndb.BlobKeyProperty()
    image_5_url = ndb.StringProperty()
    image6 = ndb.BlobKeyProperty()
    image_6_url = ndb.StringProperty()
    latlng = ndb.GeoPtProperty()
    placename = ndb.StringProperty()
    ari_1 = ndb.IntegerProperty()
    ari_2 = ndb.IntegerProperty()
    ari_3 = ndb.IntegerProperty()
    @property
    def image1_url(self):
        if self.image1:
            return images.get_serving_url(str(self.image))
        else:
            return "/img/unknown_user.png"
     
class Contention(ndb.Model):
    # Basic info.
    author = ndb.StringProperty()
    author_img = ndb.StringProperty()
    author_id = ndb.IntegerProperty()
    gpoints_key = ndb.KeyProperty(kind='GPoints', repeated=True)
    content = ndb.StringProperty()
    sure_score = ndb.IntegerProperty(default=1)
    date = ndb.DateTimeProperty(auto_now_add=True)
    other_date = ndb.StringProperty()
    branch_key = ndb.KeyProperty(kind=Branch)
    branch_name = ndb.StringProperty()
    draft = ndb.BooleanProperty(default=True)
    g_frames = ndb.IntegerProperty(default=1)
    text = ndb.StringProperty()
    description = ndb.StringProperty()
    step_count = ndb.IntegerProperty()
    tags = ndb.KeyProperty(kind=Tags, repeated=True)
    num_images = ndb.IntegerProperty(default=0)
    image1 = ndb.BlobKeyProperty()
    image_1_url = ndb.StringProperty()
    image2 = ndb.BlobKeyProperty()
    image_2_url = ndb.StringProperty()
    image3 = ndb.BlobKeyProperty()
    image_3_url = ndb.StringProperty()
    image4 = ndb.BlobKeyProperty()
    image_4_url = ndb.StringProperty()
    image5 = ndb.BlobKeyProperty()
    image_5_url = ndb.StringProperty()
    image6 = ndb.BlobKeyProperty()
    image_6_url = ndb.StringProperty()
    latlng = ndb.GeoPtProperty()
    placename = ndb.StringProperty()
    root_id = ndb.IntegerProperty()
    root_element_code = ndb.StringProperty()
    tot_element_code = ndb.StringProperty(default="0")
    elements = ndb.StructuredProperty(Elements, repeated=True)
    @property
    def image1_url(self):
        if self.image1:
            return images.get_serving_url(str(self.image))
        else:
            return "/img/unknown_user.png"

class User(golciUser):
    gpoints = ndb.IntegerProperty(default=100)

		
class GPoints(ndb.Model):
    add = ndb.BooleanProperty(default=True)
    user_key = ndb.KeyProperty(kind='User')
    user_name = ndb.StringProperty()
    replied_to_user_id = ndb.IntegerProperty()
    replied_to_user_name = ndb.StringProperty()
    points_log = ndb.StringProperty()
    contention_key = ndb.KeyProperty(kind=Contention)
    contention_id = ndb.IntegerProperty()
    element_id = ndb.StringProperty()
    replied_to_element_id = ndb.StringProperty()
    branch_name = ndb.StringProperty()
    elem_type = ndb.StringProperty()
    replied_to_elem_type = ndb.StringProperty()
    content = ndb.StringProperty()
    replied_to_content = ndb.StringProperty()
    points = ndb.IntegerProperty()   
    date = ndb.DateTimeProperty(auto_now_add=True)

#class GPoints(ndb.model):
 #   add = ndb.BooleanProperty(default=True)
 #   user_key = ndb.KeyProperty(kind='User')
 #   user_name = ndb.StringProperty()
 #   pending_addition = ndb.IntegerProperty() 
 #  pending_deduction = ndb.IntegerProperty()  
 #   date = ndb.DateTimeProperty(auto_now_add=True)

class Ari_types(ndb.Model):
    ari = ndb.StringProperty()
    description = ndb.StringProperty()      
    
    
class Ari(ndb.Model):
    contention_key = ndb.KeyProperty(kind=Contention)
    ari_type_key = ndb.KeyProperty(kind=Ari_types)
                               
    #author = ndb.UserProperty()
    content = ndb.StringProperty()
    element_id  = ndb.StringProperty()
    type  = ndb.StringProperty()    
    date = ndb.DateProperty()   
    image_URL = ndb.StringProperty()
    image = ndb.StringProperty()    
    
class golci_link(ndb.Model):
    element_key = ndb.KeyProperty(kind=Elements)
    #author = ndb.UserProperty()
    content = ndb.StringProperty()
    description = ndb.StringProperty()    
    date = ndb.DateProperty()   
    image_URL = ndb.StringProperty()
    image = ndb.StringProperty()
    
class golci_history(ndb.Model):
    contention_key = ndb.KeyProperty(Contention)
    parent_id = ndb.StringProperty()
    #author = ndb.UserProperty()
    content = ndb.StringProperty()
    description = ndb.StringProperty()    
    date = ndb.DateTimeProperty(auto_now_add=True)
    step = ndb.IntegerProperty()    
    image_URL = ndb.StringProperty()
    image = ndb.StringProperty()
