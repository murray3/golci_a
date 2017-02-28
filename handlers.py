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
#from webapp2_extras.appengine.auth.models import User
from models import GPoints
#from models import pending_GPoints
from models import Contention
from models import Elements
from models import Branch
from models import Ari
#from models import Images
from models import Ari_types
from models import golci_link
from models import golci_history
from data_functions import prefetch_refprops
from data_functions import Nest_From_LocStruct
from data_functions import element_code_update
from gpoints_functions import update_gpoints
import json

from datetime import datetime
from lib import functions
from google.appengine.ext import ndb
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
    
class LoginHandler(BaseRequestHandler):
  def get(self):
    """Handles default langing page"""
    self.render('mob_login.html')

class Argu2(BaseRequestHandler):
  def get(self):
    """Handles test argu2 page"""
    self.render('argu_form2.html')  

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
        data = data
        data["test"] = 'test of it works'
        
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
        c = Contention.get_by_id(int(con_ID))
        blob_info = upload_files[0]
        image_key = blob_info.key()
        image_url = str(get_serving_url(blob_info.key()))
        if type == "con":
            #logging.info("^^^^^^^^^^^^^^^^^^^^con_ID= " + con_ID + " ^^^^^^^^^^^^^^^^^")
            #logging.info("^^^^^^^^^^^^^^^^^^^^FILE= " + str(blob_info) + " ^^^^^^^^^^^^^^^^^")
            image_nums={1:["image1","image_1_url"],2:["image2","image_2_url"],3:["image3","image_3_url"],4:["image4","image_4_url"],5:["image5","image_5_url"],6:["image6","image_6_url"]}
            image_num = c.num_images+1 # increments from zero
            c.num_images = image_num
            # logging.info("^^^^^^^^^^^^^^^^^^^^image var= " + str(image_nums[image_num][0]) + " ^^^^^^^^^^^^^^^^^")
            # imagevar = str(image_nums[image_num][0])
            # imageUrlvar = str(image_nums[image_num][1])
            # imvar = getattr(c, imagevar)
            # imUrlvar = getattr(c, imageUrlvar)
            #image_blobkey_list = c.image
            #image_blobkey_list.append(blob_info.key())
            c.image1 = image_key
            c.image_1_url = image_url
            #image_url_list.append(str(get_serving_url(blob_info.key)))
            #c.image_url = image_url_list
            c.put()
        else:
            for e in c.elements:
                if e.element_id == the_ID:
                   e.image1 = image_key
                   e.image_1_url = image_url
            c.put()
        self.redirect(reDirStr)

class UploadUrlHandler(BaseRequestHandler):
    @user_required
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write(blobstore.create_upload_url('/upload'))
        
class IndexHandler(BaseRequestHandler):
    def get(self):
        #contention_query =  Contention.all().order('-date')
        cons = Contention.query()
        count = "0" #int(cons.count(10))+1
        #branch_query =  Branch.all().order('branch')
        branches = Branch.query()
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

class GViewHandler(BaseRequestHandler):
    def get(self):
        """Handles GET /gview"""    
        return self.render('gview.html')


class ProfileHandler(BaseRequestHandler):
    def get(self):
        """Handles GET /profile"""    
        if self.logged_in:
            sessiony = self.auth.get_user_by_session()
            u_id = sessiony['user_id']
            u = User.get_by_id(int(u_id))  
            g = GPoints.query()
            uid = u.key.id()
            ukey = ndb.Key(User, uid)
            g.filter(GPoints.user_key == ukey)
            ##g = Contention.query()
            ##g = g.filter(Contention.author_id == int(sessiony['user_id']))
            cons = g.fetch(10)
            logging.info(cons)
            #gols = Gols_user.query()
            #gols = e.filter(Gols_user.user_id == int(sessiony['user_id']))
            #for e in gols:
            #elems = e.e
            logging.info('+++++++++++++++++report 1 for g =')
            for a in cons:
               logging.info(a.content)
             #   for b in a:
              #      logging.info(b)
            logging.info("len of cons = " + str(len(cons)) )          
            logging.info('+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
            count = len(cons)
            branches = Branch.query()
            params = {
                'cons': cons,
                'branches': branches,
                'count': count,
                'user': self.current_user,
                'session': sessiony,             
                  }
            self.render('profile.html', params)
        else:
            self.redirect('/')
        
class latestgolciHandler(BaseRequestHandler):
    def get(self):
        #contention_query =  Contention.all().order('-date')
        latest = Contention.query()
        count = int(cons.count(10))+1
        data = {
            "latest" : latest,
            "count" : count,
            }
        self.response.out.write(json.dumps(data)) 


        
def branch_key(branch_name):
    """Constructs a datastore key for a Contention entity with branch_name."""
    return ndb.Key('Branch', branch_name or 'default_branch')
        
class HomeMenuHandler(BaseRequestHandler):
    def get(self):
        branch_query =  Branch.query()
        branches = branch_query #.fetch(10)
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
        reDirStr = '/cv?con_id='+str(con_id)
        lat = float(self.request.get('lat'))
        lng = float(self.request.get('lng'))
        placename = self.request.get('placename')
        if elem_id == "con":
            con = Contention.get_by_id(int(con_id))
            con.latlng = ndb.GeoPt(lat,lng)
            con.placename = placename
            con.put()
        else:
            for e in con.elements:
                if e.element_id == elem_id:
                    e.latlng = ndb.GeoPt(lat,lng)
                    e.placename = placename
            con.put()
        self.redirect(reDirStr)     

            
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
        
class PostDate(BaseRequestHandler):
    @user_required
    def post(self):
        c_id = self.request.get('con_id')
        reDirStr = '/cv?con_id='+str(c_id)
        con = Contention.get_by_id(int(c_id))
        elem_id = self.request.get('elem_id')
        elem_type = self.request.get('etype')
        date = self.request.get('date')
        if elem_type == "con":
            con.other_date = date
            con.put()
        else:
            for e in con.elements:
                if e.element_id == elem_id:
                    e.other_date = date
            con.put()
        self.redirect(reDirStr)

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
        aris =  Ari_types.query().fetch()
        #aris = ari_query.fetch(50)
        tlvl=[]
        slvl=[]
        # logging.info('+++++++++++++++++report 3 for con id ='+ contention_ID + '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        # for i in con.elements:
            # logging.info("element_id=[%s]",str(i.element_id))
            # logging.info("content=[%s]",i.content)
        # logging.info("all elements=[%s]",con.elements)
        # logging.info('++++++++++++++++++end report 3+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        for elem in con.elements:
            if len(elem.element_id) == 2:
                tlvl.append(elem)
            else:
                slvl.append(elem)
        gols=Nest_From_LocStruct(tlvl,slvl)
        logging.info("gols=[%s]",gols)
        #branch_query =  Branch.all().order('branch')
        branches = Branch.query().fetch()           
        params = {
                'upload_url':upload_url,
                'c_id':contention_ID,
                'con':con,
                'con_date':con_date,
                'gols':gols,
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
        pid = self.request.get('pid')
        content = self.request.get('content')
        ss = int(self.request.get('ss'))       
        elems = _con.elements
        e=Elements()           
        contot = _con.tot_element_code
        updated_codes = element_code_update(pid,contot)
        e.element_id = updated_codes['element_id']
        e.parent_id = pid
        e.content = content
        e.sure_score = ss
        e.branch_name = branch_name
        e.element_type = elem_type
        #logging.info("etype= "+elem_type)
        e.parent_t=parent_type
        if self.logged_in:
            logging.info('Checking currently logged in user')
            logging.info(self.current_user.name)
            sessiony = self.auth.get_user_by_session()
            e.author = self.current_user.name
            e.author_id = sessiony['user_id']
        step=int(self.request.get('step'))+1
        _con.g_frame=step
        _con.tot_element_code = updated_codes['tot_element_code']
        elems.append(e)
        _con.elements = elems
        _con.put()
        user_ID = sessiony['user_id']
        u = User.get_by_id(int(user_ID))
        cid = _con.key.id()
        ckey = _con.key  
        g = GPoints()
        uid = u.key.id()
        ukey = ndb.Key(User, uid)
        logging.info("key id = " + str(uid ))
        logging.info("ndb key = ")
        logging.info(ukey)
        g.user_key = ukey
        g.user_name = self.current_user.name
        g.points_log = "Posted " + elem_type
        g.contention_key = ckey
        g.contention_id = cid
        g.element_id = updated_codes['element_id']
        g.branch_name = branch_name
        g.points = 10
        g.elem_type = elem_type
        g.content = content
        g.put()
        logging.info('+++++++++++++++++report 1 for con id ='+ c_ID + '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        logging.info(_con.elements)
        logging.info('++++++++++++++++++end report 1+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        newcon = Contention.get_by_id(int(c_ID))
        logging.info('+++++++++++++++++report 2 for con id ='+ c_ID + '+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        for i in newcon.elements:
            logging.info(i.element_id)
            logging.info(i.content)
            logging.info(newcon.elements)
        logging.info('++++++++++++++++++end report 2+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++')
        self.redirect('/cv?con_id=%s' % _con.key.id())
        
# class TreeJsonHandler(BaseRequestHandler):
    # def treeh(self,parents,childs):
        # od={}
        
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
            
class SimpleArgHandler(BaseRequestHandler):
    @user_required
    def get(self):
        edit = self.request.get('edit')
        type = self.request.get('type')      
        #contention_query =  Contention.all().order('-date')
        #cons = contention_query.fetch(10)
        #count = int(cons.count(10))+1
        #branch_query =  Branch.order('branch')
        branches = Branch.query()
        #ari_query =  Ari_types.order('ari')
        aris = Ari_types.query()
        reasons=[]
        objections=[]
        if edit=="0" or edit=="":
            p_type = "contention"
            params = {
                'branches' : branches,
                'con' : "",
                'edit': edit,
                'p_type': p_type,
                'reasons': reasons,
                'objections': objections,
                'aris' : aris
                  }
        elif edit=="1":
            contention_ID = self.request.get('c_id')
            con = Contention.get_by_id(int(contention_ID))
            p_type = "contention"  
            elems=[]    
            reasons=[]
            objections=[]           
            params = {
                'branches': branches,
                'edit': edit,
                'p_type': p_type,
                'con': con,
                'reasons': reasons,
                'objections': objections,
                'elems': elems,
                'aris' : aris,
                #'count': count,
                  }
        return self.render('argu_form.html', params)
        
    @user_required
    def post(self):
        branchname = self.request.get('branch_name')
        edit_type = self.request.get('e_type')
        premise_type = self.request.get('p_type')
        content = self.request.get('form_content_0')
        ss = int(self.request.get('sscore_slider'))
        logging.info(self.request.POST)
        picture_url_0 = self.request.get('picture_url_0')
        if  picture_url_0 :
            field_storage = self.request.POST.multi['picture_url_0']
            mimetype = field_storage.type
            logging.info("Mimetype: {}".format(mimetype))
        user = self.current_user
        #branch_q = Branch.query(Branch.branch==branchname).fetch(1)
        #branch_key = branch_q.key()
        #branch_key = branch('key')
        #branch = Branch(parent=branch_key('Business'))
        #branch_key = branch.Key().
        #b_key = db.Key.from_path('Branch', branch)
        #tag_list1 = split(self.request.get('form_content_0'))
        tag_list=['one','two','three']
        step=0
        if premise_type == "contention":
            if edit_type == "" or edit_type == "0":  
                if self.logged_in:  
                    c = Contention()#branch_key=branch_q.key.get(), tags=tag_list )
                    c.content = content
                    c.sure_score = ss
                    c.branch_name = branchname
                    logging.info('Checking currently logged in user')
                    logging.info(self.current_user.name)
                    sessiony = self.auth.get_user_by_session()
                    c.author = self.current_user.name
                    c.author_id = sessiony['user_id']
                    c.put() 
                    user_ID = sessiony['user_id']
                    user_name = self.current_user.name
                    cid = c.key.id()
                    ## use gpoints function:
                    ## update_gpoints(user_id,user_name, branch_name,con_id,elem_id,elem_type,content,reply_user_id,reply_user_name,reply_elem_id,reply_elem_type,reply_content,category)
                    ## 
                    update_gpoints(user_ID,user_name, branchname,cid,"00","Contention",content,user_ID,user_name,"none","Con","none",1)
            elif edit_type == "1":
                contention_ID = self.request.get('c_id')
                c = Contention.get_by_id(int(contention_ID))
                if c.g_frames:
                    step = c.g_frames
                else:
                    step = 0                
                c.content = content
                c.g_frames = step + 1
                c.put()      
        self.redirect('/cv?con_id=%s' % c.key.id())
