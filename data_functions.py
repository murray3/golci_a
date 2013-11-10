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

from models import User
from models import Contention
from models import Elements
from models import Branch
from models import Ari
from models import Images
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
  return klass(**props)
    
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
        if p.image_id  is not None:                 
            pdict['image_id']=str(p.image_id)   
        else:
            pdict['image_id']="no_val_imge_id"  
        pdict['date']=str(p.date)
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
    
