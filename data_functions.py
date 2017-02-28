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
import webapp2
from webapp2_extras import auth, sessions, jinja2
from jinja2.runtime import TemplateNotFound
from jinja2 import Template

from simpleauth import SimpleAuthHandler

from google.appengine.api import images

from models import User
from models import Contention
from models import Elements
from models import Branch
from models import Ari
#from models import Images
from models import Ari_types
from models import golci_link
from models import golci_history

import json

from datetime import datetime
from lib import functions
from google.appengine.ext import db
from google.appengine.api import urlfetch


def prefetch_refprops(entities, *props):
    fields = [(entity, prop) for entity in entities for prop in props]
    ref_keys = [prop.get_value_for_datastore(x) for x, prop in fields]
    ref_entities = dict((x.key(), x) for x in db.get(set(ref_keys)))
    for (entity, prop), ref_key in zip(fields, ref_keys):
        prop.__set__(entity, ref_entities[ref_key])
    return entities
      
def _rec_con(parents,children):
    od={}
    for p in parents:
        pdict={}
        pdict['top_level']=str(p.top_level)
        pdict['parent_id']=str(p.parent_id)
        pdict['branch_name']=str(p.branch_name)     
        pdict['content']=str(p.content)
        pdict['author']=str(p.author)
        pdict['element_type']=str(p.element_type)
        pdict['description']=str(p.description)       
        pdict['date']=str(p.date)
        pdict['image1_url']=p.image1_url # get_serving_url at this point
        pid=p.key().id()
        pdict['eid']=str(pid)
        tgl=0
        for c in children:
            if c.parent_id==pid:
                if tgl==0:
                   kids=[]
                   kids.append(c)
                   tgl=1
                   #children.remove(c)
                else:
                   kids.append(c)
                   #children.remove(c)
                pdict['subnodes']=self.ins(kids,children)
        od[str(pid)]=pdict       
    return od
    
def rec_con(parents,children):
    od={}
    for p in parents:
        pdict={}
        if p.top_level is not None:
            pdict['top_level']=str(p.top_level)
        else:
            pdict['top_level']="no_val_top-level"
        if p.parent_id is not None:
            pdict['parent_id']=str(p.parent_id)
        else:
            pdict['parent_id']="no_val_parent_id"
        if p.branch_name is not None:           
            pdict['branch_name']=str(p.branch_name) 
        else:           
            pdict['branch_name']="no_val_branch_name"
        if p.content is not None:       
            pdict['content']=str(p.content)
        else:
            pdict['content']="no_val_content"
        if p.author is not None:            
            pdict['author']=str(p.author)
        else:           
            pdict['author']="no_val_author"
        if p.element_type is not None:      
            pdict['element_type']=str(p.element_type)
        else:
            pdict['element_type']="no_val_elem_type"
        if p.image_1_url  is not None:                 
            pdict['image1_url']=p.image1_url
        else:
            pdict['image1_url']="no_val_image_1_url"  
        if p.latlng  is not None:                 
            pdict['lat']=p.latlng.lat                 
            pdict['lon']=p.latlng.lon        
        if p.placename  is not None:                 
            pdict['placename']=p.placename
        pdict['date']=p.date.strftime("%a, %d. %b %y, %I:%M%p")
        if p.other_date  is not None:                 
            pdict['other_date']=p.other_date        
        pid=p.key().id()
        if pid is not None: 
            pdict['eid']=str(pid)
        else:
            pdict['eid']="no_val_pid"
            pid="no_val_pid"
        tgl=0
        for c in children:
            if c.parent_id==pid:
                if tgl==0:
                   kids=[]
                   kids.append(c)
                   tgl=1
                   #children.remove(c)
                else:
                   kids.append(c)
                   #children.remove(c)
                pdict['subnodes']=rec_con(kids,children)
        od[str(pid)]=pdict       
    return od
            
            # top_elems = len(str(con.tot_element_code)[1])
            # for idx, item in enumerate(elems):
            # if idx <= top_elems:
                # if len(str(item.element_code)) == 2:
                    # tlvl.append(f)
                # else:
                    # slvl.append(f)
                    
def Nest_From_LocStruct(parents,children):
    od={}
    for p in parents:
        pdict={}
        if p.element_id is not None:
            pdict['element_id']=str(p.element_id)
        else:
            pdict['element_id']="no_val_parent_id"
        if p.g_frame is not None:
            pdict['g_frame']=str(p.g_frame)
        else:
            pdict['g_frame']="no_val_parent_id"
        if p.content is not None:       
            pdict['content']=str(p.content)
        else:
            pdict['content']="no_val_content"
        if p.author is not None:            
            pdict['author']=str(p.author)
        else:           
            pdict['author']="no_val_author"
        if p.author_img is not None:            
            pdict['author_img']=str(p.author_img)
        else:           
            pdict['author_img']="no_val_author"
        if p.author_id is not None:            
            pdict['author_id']=str(p.author_id)
        else:           
            pdict['author_id']="no_val_author"
        if p.element_type is not None:      
            pdict['element_type']=str(p.element_type)
        else:
            pdict['element_type']="no_val_elem_type"
        # error handling for image moved to model class
        pdict['image_1_url']=p.image_1_url  
        if p.latlng  is not None:                 
            pdict['lat']=p.latlng.lat                 
            pdict['lon']=p.latlng.lon        
        if p.placename  is not None:                 
            pdict['placename']=p.placename
        pdict['date']=p.date.strftime("%a, %d. %b %y, %I:%M%p")
        if p.other_date  is not None:                 
            pdict['other_date']=p.other_date        
        tgl=0
        for c in children:
            logging.info("****************************************************************************")
            logging.info("element_id=[%s]",c.parent_id)
            logging.info("parent_id=[%s]",p.element_id)
            logging.info("****************************************************************************")
            if c.parent_id==p.element_id:
                if tgl==0:
                   kids=[]
                   kids.append(c)
                   tgl=1
                   #children.remove(c)
                else:
                   kids.append(c)
                   #children.remove(c)
                pdict['subnodes']=Nest_From_LocStruct(kids,children)
        od[str(p.element_id)]=pdict       
    return od
    
def element_code_update(pid,contot):
    # creates a new element code and updates the total element code for contention / golci
    # if len(pid) == len(contot):
       # plen = len(pid)-1 # len() gives total num of chars - not zero indexed so need to minus 2 if strings equal
       # code = int(contot[plen])+1
       # # print "code= "+ str(code)
       # #plen=plen # need to take off last line as this is going to be replaced next
       # # print "plen= "+ str(plen)
       # element_id = pid[:plen]+str(code) # all but last line of string is concatenated to new number
       # # print "pid[:plen]= "+ pid[:plen]
    # else:
    plen = len(pid) #  get len of parent code but minus 1 as strings are zero indexed
    clen = len(contot)
    code_pos = plen+1 # as we will use zero indexed list below this is ok to give us child level
    if code_pos > clen:
        code = 1
    else:
        code = int(contot[plen])+1
    logging.info("=====================" + str(code_pos) + "============" + str(clen) + "=============")
    if code_pos > clen:
        newid = list(pid)
        newid.append(str(code))
        element_id = ''.join(newid)
    else:
        newid = list(contot)
        newid[plen] = str(code)
        nnewid = newid[0:code_pos]
        element_id = ''.join(nnewid)      
    # first_part=pid[0:plen]  
    # # print  first_part     
    # if len(contot) > len(pid):
        # plen2=plen+1
        # last_part=pid[plen2:clen]
    # # print last_part
        # element_id = first_part+str(code)+last_part
    # else:
        # element_id = first_part+str(code)
    newcontot = list(contot)
    if (len(pid)+1) > clen:
        newcontot.append(str(code))
        newcontot = ''.join(newcontot)
    else:
        newcontot[plen] = str(code)
        newcontot = ''.join(newcontot)
       # print 'parent_id= '+pid
       # print 'element_id= '+element_id      
       # print 'old contot ='+contot
       # print 'newcontot ='+newcontot
    return {'element_id':element_id,'tot_element_code':newcontot}

