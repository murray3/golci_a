# -*- coding: utf-8 -*-

__author__ = 'Chris Murray - cjjmurray@gmail.com'
__website__ = 'www.golci.com'

###################################################
# functions to add and subtract gpoints
# model definition (in Models.py) is:
# class GPoints(db.Model):
#    user_id = db.IntegerProperty()
#    points_log = db.StringProperty()
#    points = db.IntegerProperty() 
#    category = db.StringProperty()
#    date = db.DateTimeProperty(auto_now_add=True)
#
###################################################
import logging
from datetime import datetime
from google.appengine.ext import ndb
from ndb import Key
from models import User
from models import Contention
from models import Branch
from models import GPoints
#from models import pending_GPoints

def update_gpoints(user_id,user_name, branch_name,con_id,elem_id,elem_type,content,reply_user_id,reply_user_name,reply_elem_id,reply_elem_type,reply_content,category):
   #
   # dict of dicts with point category's, cat scores and log text
   # nice and simple in this initial relese to get a feel for gameplay
   #
    cats = {
      '1': ["Contention","Posted a new Contention",25],
      '2': ["Element","Posted a new Element",20],
      '3': ["Ari","Posted an Ari",15],
      '4': ["Sentence Rule""Sentence rule was OK",5],
      '5': ["Hold Hands Rule","Hold hands rule was OK",5],
      '6': ["Rabbit Rule","Rabbit rule was OK",5],
      '11': ["Image","You Posted Image",5],  
      '12': ["Map","Posted Map",5],
      '13': ["Date","Posted Date",5]	    	  
    }

    g = GPoints()
    ckey = ndb.Key(Contention, con_id)  
    ukey = ndb.Key(User, user_id) 
    g.user_key = ukey
    g.user_name = user_name
    g.replied_to_user_id = reply_user_id
    g.replied_to_user_name = reply_user_name
    g.contention_key = ckey
    g.contention_id = con_id
    g.element_id = elem_id
    g.replied_to_element_id = reply_elem_id
    g.branch_name = branch_name
    g.elem_type = elem_type
    g.replied_to_elem_type = reply_elem_type
    g.content = content
    g.replied_to_content = reply_content
    for k, v, in cats.iteritems():
        if int(k) == category:
            logging.info(v[0])
            g.category = v[0]
            cat_type  = v[0]
            u = User.get_by_id(int(user_id))
            ex_user_points = u.gpoints
            if cat_type == "Ari":
                u = User.get_by_id(int(user_id))
                ex_user_pending_add_points = u.pending_addition
                u.pending_addition = ex_user_pending_add_points + int(v[2])
                u.put()
                rt_u = User.get_by_id(int(reply_user_id))
                rt_user_pending_deduct_points  = rt_u.pending_deduction
                rt_u._u.pending_deduction = rt_user_pending_deduct_points + int(v[2])
                rt_u.put()
                pgp = pending_gpoints()
                g.points_log = v[1]
                g.pending_addition = int(v[2])
                g.pending_deduction = int(v[2])
            else:
                u.gpoints = ex_user_points+int(v[2])
                u.put()
                g.points_log = v[1]
                g.points = int(v[2])
    g.put()

	
	
	
	
