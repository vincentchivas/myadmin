# -*- coding: utf-8 -*-
"""
@author: zhhfang
@date: 2014-07-15
@description: config the modules under db to have a _db configured each
"""

from provisionadmin.db.config import config
import userdb
import presetdb

print 'init app db'
config(userdb)
config(presetdb)
