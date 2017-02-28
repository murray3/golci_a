# -*- coding: utf-8 -*-

__author__ = 'Chris Murray - cjjmurray@gmail.com'
__website__ = 'www.golci.com'
import os
import logging
if os.environ.get('SERVER_SOFTWARE','').startswith('Development'):
    import secrets_local as secrets
else:
    import secrets
import re

from ndb import Key
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore
from google.appengine.api.images import get_serving_url
import webapp2
from webapp2_extras import auth, sessions, jinja2
from jinja2.runtime import TemplateNotFound
from jinja2 import Template

from simpleauth import SimpleAuthHandler

from models import User
from models import Contention
from models import Elements
from models import Branch
from models import Ari
from models import Images
from models import Ari_types
from models import golci_link
from models import golci_history
from data_functions import prefetch_refprops
from data_functions import rec_con
import json

from datetime import datetime
from lib import functions
from google.appengine.ext import db
from google.appengine.api import urlfetch

from wtforms import Form
from wtforms import fields
from wtforms import validators

def user_required(handler):
    """
         Decorator for checking if there's a user associated with the current session.
         Will also fail if there's no session present.
    """

    def check_login(self, *args, **kwargs):
        auth = self.auth
        if not auth.get_user_by_session():
            # If handler has no login_url specified invoke a 403 error
            try:
                self.redirect('/login')
            except (AttributeError, KeyError), e:
                self.abort(403)
        else:
            return handler(self, *args, **kwargs)

    return check_login   
    
class BaseRequestHandler(webapp2.RequestHandler):
  def dispatch(self):
    # Get a session store for this request.
    self.session_store = sessions.get_store(request=self.request)
    
    try:
      # Dispatch the request.
      webapp2.RequestHandler.dispatch(self)
    finally:
      # Save all sessions.
      self.session_store.save_sessions(self.response)
  
  @webapp2.cached_property    
  def jinja2(self):
    """Returns a Jinja2 renderer cached in the app registry"""
    return jinja2.get_jinja2(app=self.app)
    
  @webapp2.cached_property
  def session(self):
    """Returns a session using the default cookie key"""
    return self.session_store.get_session()
    
  @webapp2.cached_property
  def auth(self):
      return auth.get_auth()
  
  @webapp2.cached_property
  def current_user(self):
    """Returns currently logged in user"""
    user_dict = self.auth.get_user_by_session()
    return self.auth.store.user_model.get_by_id(user_dict['user_id'])
      
  @webapp2.cached_property
  def logged_in(self):
    """Returns true if a user is currently logged in, false otherwise"""
    return self.auth.get_user_by_session() is not None
  
      
  def render(self, template_name, template_vars={}):
    # Preset values for the template
    values = {
      'url_for'    : self.uri_for,
      'logged_in'  : self.logged_in
    }
    
    # Add manually supplied template values
    values.update(template_vars)
    
    # read the template or 404.html
    try:
      self.response.write(self.jinja2.render_template(template_name, **values))
    except TemplateNotFound:
      self.abort(404)

  def head(self, *args):
    """Head is used by Twitter. If not there the tweet button shows 0"""
    pass
    
    
class RootHandler(BaseRequestHandler):
  def get(self):
    """Handles default langing page"""
    self.render('index.html')
    
# class SimpleArgHandler(BaseRequestHandler):
  # def get(self):
    # """Handles default langing page"""
    # self.render('argu_form.html')
    
class LoginHandler(BaseRequestHandler):
  def get(self):
    """Handles default langing page"""
    self.render('mob_login.html')

class Argu2(BaseRequestHandler):
  def get(self):
    """Handles test argu2 page"""
    self.render('argu_form2.html')
    
class ProfileHandler(BaseRequestHandler):
  def get(self):
    """Handles GET /profile"""    
    if self.logged_in:
      self.render('profile.html', {
        'user': self.current_user, 'session': self.auth.get_user_by_session()
      })
    else:
      self.redirect('/')


      

class AuthHandler(BaseRequestHandler, SimpleAuthHandler):
  """Authentication handler for OAuth 2.0, 1.0(a) and OpenID."""
  
  USER_ATTRS = {
    'google'   : {
      'picture': 'avatar_url',
      'name'   : 'name',
      'link'   : 'link'
    },
    'facebook' : {
      'id'     : lambda id: ('avatar_url', 'http://graph.facebook.com/{0}/picture?type=large'.format(id)),
      'name'   : 'name',
      'link'   : 'link'
    },
    'windows_live': {
      'avatar_url': 'avatar_url',
      'name'      : 'name',
      'link'      : 'link'
    },
    'twitter'  : {
      'profile_image_url': 'avatar_url',
      'screen_name'      : 'name',
      'link'             : 'link'
    },
    'linkedin' : {
      'picture-url'       : 'avatar_url',
      'first-name'        : 'name',
      'public-profile-url': 'link'
    },
    'openid'   : {
      'id'      : lambda id: ('avatar_url', '/img/missing-avatar.png'),
      'nickname': 'name',
      'email'   : 'link'
    }
  }
  
  def _on_signin(self, data, auth_info, provider):
    """Callback whenever a new or existing user is logging in.
     data is a user info dictionary.
     auth_info contains access token or oauth token and secret.
    """
    auth_id = '%s:%s' % (provider, data['id'])
    logging.info('Looking for a user with id %s' % auth_id)
    
    user = self.auth.store.user_model.get_by_auth_id(auth_id)
    if user:
      logging.info('Found existing user to log in')
      # existing user. just log them in.
      self.auth.set_session(
        self.auth.store.user_to_dict(user)
      )
      
    else:
      # check whether there's a user currently logged in
      # then, create a new user if nobody's signed in, 
      # otherwise add this auth_id to currently logged in user.
      if self.logged_in:
        logging.info('Updating currently logged in user')
        
        u = self.current_user
        u.auth_ids.append(auth_id)
        u.populate(**self._to_user_model_attrs(data, self.USER_ATTRS[provider]))
        u.put()
        
      else:
        logging.info('Creating a brand new user')
        
        ok, user = self.auth.store.user_model.create_user(
          auth_id, **self._to_user_model_attrs(data, self.USER_ATTRS[provider])
        )
        
        if ok:
          self.auth.set_session(
            self.auth.store.user_to_dict(user)
          )
      
    # show them their profile data
    self.redirect('/profile')

  def logout(self):
    self.auth.unset_session()
    self.redirect('/index')
    
  def _callback_uri_for(self, provider):
    return self.uri_for('auth_callback', provider=provider, _full=True)
    
  def _get_consumer_info_for(self, provider):
    """Returns a tuple (key, secret) for auth init requests."""
    return secrets.AUTH_CONFIG[provider]
    
  def _to_user_model_attrs(self, data, attrs_map):
    user_attrs = {}
    for k, v in data.iteritems():
      if k in attrs_map:
        key = attrs_map[k]
        if isinstance(key, str):
          user_attrs.setdefault(key, v)
        else:
          user_attrs.setdefault(*key(v))
          
    return user_attrs
    

class FileServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self):
        ImageBlobKey = self.request.get("id")
        blob_info = blobstore.BlobInfo.get(ImageBlobKey)
        #self.send_blob(blob_info)
        self.response.out.write("%s" % get_serving_url(blob_info,42))

class aaaa(webapp2.RequestHandler):
    def get(self):
        a =  Ari_types()
        a.ari = "Ad Hominem"
        a.description = "Against the person"
        a.put()
        a =  Ari_types()
        a.ari = "Ad Hominem Tu Quoque"
        a.description = "You Too Fallacy"
        a.put()
 
class ImageHandler(webapp2.RequestHandler):
    def get(self):
        #logging.info("T!!!!!!!!!!!!!!!!!!!!!!HE value of contention is %s", self.request.get("entity_id"))
        type = self.request.get("type")
        the_ID = self.request.get("entity_id")
        if not the_ID==None:
            if type == "con":
                con = Images.get_by_id(int(the_ID))
                self.response.headers['Content-Type'] = 'image/jpeg'
                self.response.out.write(con.image)
            elif type == "elem":
                elem = Images.get_by_id(int(the_ID))
                self.response.headers['Content-Type'] = 'image/jpeg'
                self.response.out.write(elem.image)
            else:
                self.redirect('/static/ok.png')
            
class FileUploadHandler(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        type = self.request.get("i_type")
        the_ID = self.request.get("i_entity_id")
        con_ID = self.request.get("con_id")
        reDirStr = '/cv?con_id='+str(con_ID)
        image_Num = self.request.get("i_num")
        upload_files = self.get_uploads('file') 
        if type == "con":
            c = Contention.get_by_id(int(the_ID))
            blob_info = upload_files[0]
            c.image1=blob_info.key()
            c.put()
        else:
            e = Elements.get_by_id(int(the_ID))
            blob_info = upload_files[0]
            e.image1=blob_info.key()
            e.put()
        self.redirect(reDirStr)

class UploadUrlHandler(BaseRequestHandler):
    @user_required
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(blobstore.create_upload_url('/upload'))
        
class IndexHandler(BaseRequestHandler):
    def get(self):
        contention_query =  Contention.all().order('-date')
        cons = contention_query.fetch(10)
        count = "0" #int(cons.count(10))+1
        branch_query =  Branch.all().order('branch')
        branches = branch_query.fetch(10)
        #images = con.images.fetch(10)
        
        # if users.get_current_user():
            # url = users.create_logout_url(self.request.uri)
            # url_linktext = 'Logout'
        # else:
            # url = users.create_login_url(self.request.uri)
            # url_linktext = 'Login'


        params = {
                'cons': cons,
                'branches': branches,
                'count': count,
                  }
        return self.render('index.html', params)
        
class latestgolciHandler(BaseRequestHandler):
    def get(self):
        contention_query =  Contention.all().order('-date')
        latest = contention_query.fetch(10)
        count = int(cons.count(10))+1
        data = {
            "latest" : latest,
            "count" : count,
            }
        self.response.out.write(json.dumps(data)) 

class SimpleArgHandler(BaseRequestHandler):
    @user_required
    def get(self):
        edit = self.request.get('edit')
        type = self.request.get('type')      
        #contention_query =  Contention.all().order('-date')
        #cons = contention_query.fetch(10)
        #count = int(cons.count(10))+1
        branch_query =  Branch.all().order('branch')
        branches = branch_query.fetch(10)
        ari_query =  Ari_types.all().order('ari')
        aris = ari_query.fetch(50)
        if edit=="0" or edit=="":
            p_type = "contention"
            params = {
                'branches' : branches,
                'con' : "",
                'reasons' : "",
                'objections' : "",
                'edit': edit,
                'p_type': p_type,
                'aris' : aris
                  }
        elif edit=="1":
            contention_ID = self.request.get('c_id')
            con = Contention.get_by_id(int(contention_ID))
            p_type = "contention" 
            reasons = {}
            objections = {}
            if con:
                elems = con.elements.fetch(50)
                count = int(elems.count(20))+1
                rsn =0
                objn =0
                for f in elems:
                    if f.top_level == 1:
                        if f.element_type == 'reason':
                            rsn=rsn+1
                            reasons['reason'+str(rsn)]=f                      
                        if f.element_type == 'objection':
                            objn=objn+1
                            objections['objection'+str(objn)]=f             
            params = {
                'branches': branches,
                'edit': edit,
                'p_type': p_type,
                'con': con,
                'elems': elems,
                'reasons': reasons,
                'objections': objections,
                'aris' : aris,
                #'count': count,
                  }
        elif edit=="2":
            contention_ID = self.request.get('c_id')
            con = Contention.get_by_id(int(contention_ID))
            p_type = "element"
            reasons = []
            objections = []
            if con:
                elems = con.elements.fetch(50)
                count = int(elems.count(20))+1
                elem_ID = int(self.request.get('e_id'))
                rsn =0
                objn =0
                for f in elems:
                    if f.parent_id == elem_ID:
                        if f.element_type == 'reason':
                            rsn=rsn+1
                            reasons['reason'+str(rsn)]=f                      
                        if f.element_type == 'objection':
                            objn=objn+1
                            objections['objection'+str(objn)]=f 
            #edit_gols['subnodes']=slvl
            elem_ID = self.request.get('e_id')
            elem = Elements.get_by_id(int(elem_ID))         
            params = {
                'branches': branches,
                'edit': edit,
                'p_type': p_type,
                'con': con,
                'elem': elem,
                'reasons': reasons,
                'objections': objections,
                'aris' : aris,
                'form_url': blobstore.create_upload_url('/upload')
                #'count': count,
                  }

            
        
        # if users.get_current_user():
            # url = users.create_logout_url(self.request.uri)
            # url_linktext = 'Logout'
        # else:
            # url = users.create_login_url(self.request.uri)
            # url_linktext = 'Login'

        return self.render('argu_form.html', params)
        
    @user_required
    def post(self):
        branch_name = self.request.get('branch_name')
        edit_type = self.request.get('e_type')
        premise_type = self.request.get('p_type')
        logging.info(self.request.POST)
        picture_url_0 = self.request.get('picture_url_0')
        if  picture_url_0 :
            field_storage = self.request.POST.multi['picture_url_0']
            mimetype = field_storage.type
            logging.info("Mimetype: {}".format(mimetype))
        user = self.current_user
        branch_q = db.GqlQuery("SELECT * FROM Branch WHERE branch = :1", branch_name)
        branch = branch_q.get()
        #branch = Branch(parent=branch_key('Business'))
        #branch_key = branch.Key().id()
        #b_key = db.Key.from_path('Branch', branch)
        #tag_list1 = split(self.request.get('form_content_0'))
        tag_list=['one','two','three']
        step=0
        if premise_type == "contention":
            if edit_type == "0":    
                c = Contention(branch_key=branch, tags=tag_list )
                c.content = self.request.get('form_content_0')
                c.branch_name = branch_name
                if self.logged_in:
                    logging.info('Checking currently logged in user')
                    logging.info(self.current_user.name)
                    sessiony = self.auth.get_user_by_session()
                    c.author = self.current_user.name
                    c.author_id = sessiony['user_id']
                c.put()
                if picture_url_0 != '':
                    i = Images(branch_key=branch, contention_key=c )
                    i.image = db.Blob(picture_url_0)
                    i.element_type = "contention"
                    i.description = self.request.get('image_description_0')
                    if self.logged_in:
                        i.author = self.current_user.name
                        i.author_id = sessiony['user_id']
                    i.put()
                    c.image_id=i.key().id()
                    c.put()
            elif edit_type == "1":
                contention_ID = self.request.get('c_id')
                con = Contention.get_by_id(int(contention_ID))
                if con.g_frames:
                    step = con.g_frames
                else:
                    step = 0                
                gframe = Elements(contention_key=con, element_type="contention", gframe=step, image_id=con.image_id, author=con.author, author_id=con.author_id, content=con.content )
                gframe.put()
                con.content = self.request.get('form_content_0')
                con.g_frames = step + 1
                if picture_url_0 != '':
                    i = Images(branch_key=branch, contention_key=c )
                    i.image = db.Blob(picture_url_0)
                    i.element_type = "contention"
                    i.description = self.request.get('image_description_0')
                    if self.logged_in:
                        sessiony = self.auth.get_user_by_session()
                        i.author = self.current_user.name
                        i.author_id = sessiony['user_id']
                    i.put()
                    con.image_id=i.key().id()
                con.put()
        if premise_type == "element":
            contention_ID = self.request.get('c_id')
            con = Contention.get_by_id(int(contention_ID))          
            if edit_type == "0":    
                c = Elements(contention_key=con, gframe=step)
                c.content = self.request.get('form_content_0')
                c.branch_name = branch_name
                if self.logged_in:
                    logging.info('Checking currently logged in user')
                    logging.info(self.current_user.name)
                    sessiony = self.auth.get_user_by_session()
                    c.author = self.current_user.name
                    c.author_id = sessiony['user_id']
                c.put()
                if picture_url_0 != '':
                    i = Images(branch_key=branch, contention_key=con )
                    i.image = db.Blob(picture_url_0)
                    i.element_type = "contention"
                    i.description = self.request.get('image_description_0')
                    if self.logged_in:
                        i.author = self.current_user.name
                        i.author_id = sessiony['user_id']
                    i.put()
                    c.image_id=i.key().id()
                    c.put()
                    con.g_frames = step+1
                    con.put()
            elif edit_type == "1":
                contention_ID = self.request.get('c_id')
                con = Contention.get_by_id(int(contention_ID))
                gframe = Elements(contention_key=con, element_type="contention", gframe=step, image_id=con.image_id, author=con.author, author_id=con.author_id, content=con.content )
                gframe.put()
                con.content = self.request.get('form_content_0')
                con.g_frames = step + 1
                if picture_url_0 != '':
                    i = Images(branch_key=branch, contention_key=c )
                    i.image = db.Blob(picture_url_0)
                    i.element_type = "contention"
                    i.description = self.request.get('image_description_0')
                    if self.logged_in:
                        sessiony = self.auth.get_user_by_session()
                        i.author = self.current_user.name
                        i.author_id = sessiony['user_id']
                    i.put()
                    con.image_id=i.key().id()
                con.put()
        
        
        reasons = int(self.request.get('_reasons'))
        objections = int(self.request.get('_objections'))
        if reasons > 0:
            if edit_type == "0":
                for reas in range(1, reasons+1):
                    pic = 'picture_url_' + str(reas)
                    pict = self.request.get(pic)
                    if premise_type == "contention":
                        r = Elements(contention_key=c, top_level=1, gframe=step)
                    if premise_type == "element":
                        r = Elements(contention_key=con, top_level=0, gframe=step, parent_id = c.key().id())
                    r.element_type='reason'
                    if pict != '':
                        i = Images(branch_key=branch, contention_key=c )
                        i.image = db.Blob(picture_url_0)
                        i.element_type = "contention"
                        i.description = self.request.get('image_description_0')
                        if self.logged_in:
                            sessiony = self.auth.get_user_by_session()
                            i.author = self.current_user.name
                            i.author_id = sessiony['user_id']
                        i.put()
                    #r.image_id=i.key().id()
                    rcon = 'form_reason_'+str(reas)
                    r.content = self.request.get(rcon)
                    r.branch_name = branch_name
                    if self.logged_in:
                        sessiony = self.auth.get_user_by_session()
                        r.author = self.current_user.name
                        r.author_id = sessiony['user_id']
                    r.put()

            elif edit_type == "1":
                for reas in range(1, reasons+1):
                    pic = 'picture_url_' + str(reas)
                    pict = self.request.get(pic)
                    el_id = 'form_reason_'+str(reas)+'_'
                    e_id = self.request.get(el_id)
                    rcon = 'form_reason_'+str(reas)
                    r_content = self.request.get(rcon)
                    logging.info("this is test")
                    logging.info('form_reason_'+str(reas)+'_')
                    r = Elements.get_by_id(int(e_id))   
                    if r_content != r.content:                  
                        if premise_type == "contention":
                            gframe = Elements(contention_key=con, element_type="reason", gframe=step, image_id=r.image_id, author=r.author, author_id=r.author_id, content=r.content )
                            gframe.put()
                            r.content = r_content
                            r.g_frame = con.g_frames
                        if premise_type == "element":
                            r = Elements(contention_key=con,parent_id = c.key().id())
                            r.top_level = 0
                        r.element_type='reason'
                        if pict != '':
                            i = Images(branch_key=branch, contention_key=c )
                            i.image = db.Blob(picture_url_0)
                            i.element_type = "contention"
                            i.description = self.request.get('image_description_0')
                            if self.logged_in:
                                sessiony = self.auth.get_user_by_session()
                                i.author = self.current_user.name
                                i.author_id = sessiony['user_id']
                            i.put()
                        #r.image_id=i.key().id()
                        rcon = 'form_reason_'+str(reas)
                        r.content = self.request.get(rcon)
                        r.branch_name = branch_name
                        if self.logged_in:
                            sessiony = self.auth.get_user_by_session()
                            r.author = self.current_user.name
                            r.author_id = sessiony['user_id']
                        r.put()     
        if objections > 0:
            for objs in range(1,objections+1):
                picobjs = objs + 5
                pic = 'picture_url_' + str(picobjs)
                pict = self.request.get(pic)
                o = Elements(contention_key=c)
                if premise_type == "contention":
                    o = Elements(contention_key=c)
                    o.top_level = 1
                if premise_type == "element":
                    o = Elements(contention_key=con,parent_id = c)
                    o.top_level = 0
                if pict != '':
                    o.image = db.Blob(urlfetch.Fetch(pict).content)
                ocon = 'form_objection_'+str(objs)
                o.content = self.request.get(ocon)
                o.branch_name = branch_name
                if self.logged_in:
                    sessiony = self.auth.get_user_by_session()
                    o.author = self.current_user.name
                    o.author_id = sessiony['user_id']
                o.put()
        
        self.redirect('/conv?con_id=%s' % c.key().id())
        

  
        
    def branch_key(branch_name):
        """Constructs a datastore key for a Contention entity with branch_name."""
        return db.Key.from_path('Branch', branch_name or 'default_branch')
        
class HomeMenuHandler(BaseRequestHandler):
    def get(self):
        branch_query =  Branch.all().order('branch')
        branches = branch_query.fetch(10)

        params = {'branches':branches}
        return self.render('menu.html', params)
        
class MapEditHandler(BaseRequestHandler):
    def get(self):
        etype = self.request.get('etype')
        con_id = self.request.get('con_id')
        if etype == "elem":
            elem_id = self.request.get('elem_id')
            params = {
                      'etype':etype,
                      'con_id':con_id,
                      'elem_id':elem_id,
                     }
        else:
            params = {
                      'etype':etype,
                      'elem_id':'con',
                      'con_id':con_id
                     }
        return self.render('map.html', params)

    @user_required
    def post(self):
        etype = self.request.get('etype')
        elem_id = self.request.get('elem_id')
        con_id = self.request.get('con_id')
        lat = float(self.request.get('lat'))
        lng = float(self.request.get('lng'))
        placename = self.request.get('placename')
        if elem_id == "con":
            con = Contention.get_by_id(int(con_id))
            con.latlng = db.GeoPt(lat,lng)
            con.placename = placename
            con.put()
        else:
            elem = Elements.get_by_id(int(elem_id))
            elem.latlng = db.GeoPt(lat,lng)
            elem.placename = placename
            elem.put()      

            
class BranchHandler(BaseRequestHandler):
    def get(self):
        #branch = self.request.get('branch')
        branch_name = self.request.get('branch_name')
        #branch_key = db.Key.from_path(branch)
        branch_q = db.GqlQuery("SELECT * FROM Branch WHERE branch = :1", branch_name)
        branch = branch_q.get()
        
        #contention_query =  Contention.all().order('date')
        cons = branch.contentions.fetch(20)
        count = int(cons.count(20))+1
        # if users.get_current_user():
            # url = users.create_logout_url(self.request.uri)
            # url_linktext = 'Logout'
        # else:
            # url = users.create_login_url(self.request.uri)
            # url_linktext = 'Login'


        params = {
                'cons':cons,
                'branch_name':branch_name,
                'count': count,
                }
        return self.render('branch.html', params)
        
class RecursiveContentHandler(BaseRequestHandler):
    def get(self):
        contention_ID = self.request.get('con_id')
        con = Contention.get_by_id(int(contention_ID))
        elems=[]
        count=0
        if con:
            elems = con.elements.fetch(50)
            count = int(elems.count(20))+1
        tlvl=[]
        slvl=[]
        for f in elems:
            if f.top_level == 1:
                tlvl.append(f)
            else:
                slvl.append(f)
        gols=rec_con(tlvl,slvl)
        objections=[]
        reasons=[]
        rcount=0
        ocount=0
        ccount=0
        #contention_query =  Contention.all().order('date')
        if con:
            if elems:
                for r in elems:
                    if r.element_type=='reason':
                        reasons.append(r)
                        rcount = rcount+1
                for o in elems:
                    if o.element_type=='objection':
                        objections.append(o)
                        ocount = ocount+1
            ccount = int(len(elems))        
        params = {
                'con':con,
                'reasons':reasons,
                'objections':objections,
                'ccount': ccount,
                'rcount': rcount,
                'ocount': ocount,
                'elems':elems,
                'gols':gols,
                'count': count
                }
        return self.render('recursive_contention.html', params)


class ContentViewHandler(BaseRequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        contention_ID = self.request.get('con_id')
        con = Contention.get_by_id(int(contention_ID))
        con_date = con.date.strftime("%a, %d. %b %y, %I:%M%p")
        # for x in xrange(1, 11):
            # image_num = "image" + str(x)      
            # if con(image_num):
                # con_image_urls[x]= get_serving_url(con(image_num))
        #return images.get_serving_url(self.image1)
        ari_query =  Ari_types.all().order('ari')
        aris = ari_query.fetch(50)
        count=0
        if con:
            elems = con.elements.fetch(50)
            count = int(elems.count(20))+1
        tlvl=[]
        slvl=[]
        for f in elems:
            if f.top_level == 1:
                tlvl.append(f)
            else:
                slvl.append(f)
        gols=rec_con(tlvl,slvl)
        objections=[]
        reasons=[]
        rcount=0
        ocount=0
        ccount=0
        #contention_query =  Contention.all().order('date')
        if con:
            if elems:
                for r in elems:
                    if r.element_type=='reason':
                        reasons.append(r)
                        rcount = rcount+1
                for o in elems:
                    if o.element_type=='objection':
                        objections.append(o)
                        ocount = ocount+1
            ccount = int(len(elems))                
        params = {
                'upload_url':upload_url,
                'c_id':contention_ID,
                'con':con,
                'con_date':con_date,
                'reasons':reasons,
                'objections':objections,
                'ccount': ccount,
                'rcount': rcount,
                'ocount': ocount,
                'elems':elems,
                'gols':gols,
                'count': count,
                'aris': aris
                }
        return self.render('contention_view.html', params)

    @user_required
    def post(self):
        c_ID = self.request.get('con_id')
        _con = Contention.get_by_id(int(c_ID))
        branch_name = self.request.get('branch')
        elem_type = self.request.get('etype')
        parent_type = self.request.get('ptype')
        content = self.request.get('content')
        step=int(self.request.get('step'))+1
        e = Elements(contention_key=_con, gframe=step)
        if parent_type == "con":
            e.top_level=1
        else:
            e.parent_id = int(self.request.get('pid'))
        e.content = content
        e.branch_name = branch_name
        e.element_type=elem_type
        e.parent_t=parent_type
        if self.logged_in:
            logging.info('Checking currently logged in user')
            logging.info(self.current_user.name)
            sessiony = self.auth.get_user_by_session()
            e.author = self.current_user.name
            e.author_id = sessiony['user_id']
        e.put()
        _con.g_frames=step
        _con.put()
        
class PostDate(BaseRequestHandler):
    @user_required
    def post(self):
        c_id = self.request.get('con_id')
        con = Contention.get_by_id(int(c_id))
        elem_id = self.request.get('elem_id')
        elem_type = self.request.get('etype')
        date = self.request.get('date')
        if elem_type == "con":
            con.other_date = date
            con.put()
        else:
            e = Elements.get_by_id(int(elem_id))
            e.other_date = date
            e.put()

class ContentionHandler(BaseRequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/upload')
        contention_ID = self.request.get('con_id')
        con = Contention.get_by_id(int(contention_ID))
        con_date = con.date.strftime("%a, %d. %b %y, %I:%M%p")
        # for x in xrange(1, 11):
            # image_num = "image" + str(x)      
            # if con(image_num):
                # con_image_urls[x]= get_serving_url(con(image_num))
        #return images.get_serving_url(self.image1)
        count=0
        ari_query =  Ari_types.all().order('ari')
        aris = ari_query.fetch(50)
        if con:
            elems = con.elements.fetch(50)
            count = int(elems.count(20))+1
        tlvl=[]
        slvl=[]
        for f in elems:
            if f.top_level == 1:
                tlvl.append(f)
            else:
                slvl.append(f)
        gols=rec_con(tlvl,slvl)
        objections=[]
        reasons=[]
        rcount=0
        ocount=0
        ccount=0
        #contention_query =  Contention.all().order('date')
        if con:
            if elems:
                for r in elems:
                    if r.element_type=='reason':
                        reasons.append(r)
                        rcount = rcount+1
                for o in elems:
                    if o.element_type=='objection':
                        objections.append(o)
                        ocount = ocount+1
            ccount = int(len(elems))  
        branch_query =  Branch.all().order('branch')
        branches = branch_query.fetch(10)           
        params = {
                'upload_url':upload_url,
                'c_id':contention_ID,
                'con':con,
                'con_date':con_date,
                'reasons':reasons,
                'objections':objections,
                'ccount': ccount,
                'rcount': rcount,
                'ocount': ocount,
                'elems':elems,
                'gols':gols,
                'count': count,
                "branches":branches,
                'aris': aris
                }
        return self.render('contention_panel_view.html', params)

    @user_required
    def post(self):
        c_ID = self.request.get('con_id')
        _con = Contention.get_by_id(int(c_ID))
        branch_name = self.request.get('branch')
        elem_type = self.request.get('etype')
        parent_type = self.request.get('ptype')
        content = self.request.get('content')
        step=int(self.request.get('step'))+1
        e = Elements(contention_key=_con, g_frame=step)
        if parent_type == "con":
            e.top_level=1
        else:
            e.parent_id = int(self.request.get('pid'))
        e.content = content
        e.branch_name = branch_name
        e.element_type=elem_type
        logging.info("etype= "+elem_type)
        e.parent_t=parent_type
        if self.logged_in:
            logging.info('Checking currently logged in user')
            logging.info(self.current_user.name)
            sessiony = self.auth.get_user_by_session()
            e.author = self.current_user.name
            e.author_id = sessiony['user_id']
        e.put()
        _con.g_frames=step
        _con.put()
                
class TreeJsonHandler(BaseRequestHandler):
    def treeh(self,parents,childs):
        od={}
        od1={}
        pdict={}
        tog=1
        for p in parents:
            oname='name_'+str(tog)
            ochildren='children_'+str(tog)
            pid=p.key().id()
            kids=[]
            for c in childs:
                if int(c.parent_id)==int(pid):
                    kids.append(c)
            kids.sort()
            tgl=1
            for k in kids:
                kk=[]
                kk.append(k)
                iname='name_'+str(tgl)
                ichildren='children_'+str(tgl)
                pdict[iname]=str(k.content)                       
                pdict[ichildren]=[self.treeh(kk,childs)]
                tgl=tgl+1
            od[oname]=p.content
            od[ochildren]=[pdict]
            tog=tog+1             
        return od
        
    def treestring(self,tg,tgl,parents,childs):
        stringy=""
        tog=0
        _step=5
        for p in parents:       
            pstring=""
            #if not tog == 0 or len(parents) == tog:
                #pstring = ',' + pstring
            pid=p.key().id()
            pstring = pstring +'{\"name\": \"' + p.content +'\",\"step\": \"' + str(_step) +'\",\"id\": \"' + str(pid) +'\"'
            cstring = ',\"children\": ['
            test_cstring=0
            kids=[]
            for c in childs:
                if int(c.parent_id)==int(pid):
                    test_cstring=1
                    kids.append(c)
            kids.sort()
            ccstring=""
            togg=0
            togl=len(kids)
            if test_cstring==1:
                for k in kids:
                    kk=[]
                    kk.append(k)
                    ccstring = ccstring + self.treestring(0,togl,kk,childs)
                    if not togg == togl-1:
                        cccstring=","
                    else:
                        cccstring="" 
                    ccstring = ccstring + cccstring
                    togg=togg+1                    
                ccstring = cstring + ccstring + ']'
            pstring = pstring + ccstring  + '}'
            if not len(parents) == tog+1:
                pstring = pstring + ',' 
            tog=tog+1 
            stringy= stringy + pstring
        return stringy
        
    def get(self):
        #branch = self.request.get('branch')
        contention_ID = self.request.get('con_id')
        #con_key = db.Key.from_path('Contention',int(contention_ID))
        con = Contention.get_by_id(int(contention_ID))
        #con_q = db.GqlQuery("SELECT * from Contention where __key__ = key; key=KEY('Contention', contention_ID))
        #con = con_q.get()
        elems=[]
        count=0
        #contention_query =  Contention.all().order('date')
        if con:
            elems = con.elements.fetch(50)
            count = int(elems.count(20))+1
        tl=[]
        sl=[]
        for f in elems:
            if f.top_level == 1:
                tl.append(f)
            else:
                sl.append(f)
        #gols=self.treeh(tl,sl)
        # for p in tl:
            # od={}
            # od["C1"]=p.content
            # gols.append(self.flatpack(p,sl,od,2))

        #self.response.out.write(json.dumps(gols))
        stringy = ""
        vari = '{\"name\": \"' + con.content +'\",\"step\": \"' + "5" +'\",\"this_step\": \"' + "5" +'\",\"total\": \"' + "5" +'\",\"id\": \"' + contention_ID + '\",\"children\": [' + self.treestring(0,len(tl),tl,sl) + ']}'
                
        params = { 
                 'vari':vari,
                 'con':con,
                 'tl':tl,
                 'sl':sl
                 }
        #return tmpl.render()
        self.render('test1.json', params)
        
class TreeHandler(BaseRequestHandler):        
    def get(self):
        """Handles tree view page"""
        contention_ID = self.request.get('con_id')
        #con_key = db.Key.from_path('Contention',int(contention_ID))
        con = Contention.get_by_id(int(contention_ID))
        params = { 
                 'con':con
                 }
        self.render('tree-2.html', params)

        
class DynamicHandler(BaseRequestHandler):
    def get(self):
        #branch = self.request.get('branch')
        contention_ID = self.request.get('con_id')
        #con_key = db.Key.from_path('Contention',int(contention_ID))
        con = Contention.get_by_id(int(contention_ID))
        #con_q = db.GqlQuery("SELECT * from Contention where __key__ = key; key=KEY('Contention', contention_ID))
        #con = con_q.get()
        elems=[]
        count=0
        #contention_query =  Contention.all().order('date')
        if con:
            elems = con.elements.fetch(50)
            count = int(elems.count(20))+1
        tl=[]
        sl=[]
        for f in elems:
            if f.top_level == 1:
                tl.append(f)
            else:
                sl.append(f)
        # if users.get_current_user():
            # url = users.create_logout_url(self.request.uri)
            # url_linktext = 'Logout'
        # else:
            # url = users.create_login_url(self.request.uri)
            # url_linktext = 'Login'
        gols=rec_con(tl,sl)
        #listy={'Contention': {'Reason_1': {'Reason_1a': {'Reason_1b': {}}},'Reason_2': {}}}
        params = {
                'con':con,
                'elems':elems,
                'count': count,
                'gols':gols
                }
        return self.render('dynamic.html', params)
        
class Tester(BaseRequestHandler):       
    def get(self):
        params = {} 
        return self.render('test.html', params)
        
    def post(self):
        field_storage = self.request.POST["file"]
        try:
            mimetype = field_storage.type
            self.response.write("Mimetype: {}".format(mimetype))
            self.response.write(self.request.POST)
        except:
            self.response.write("No FieldStorage object, field_storage={}".format(field_storage))    
            
class TestMob(BaseRequestHandler):
    def get(self):
        """Handles mobile testing page"""
        return self.render('mobtest.html')