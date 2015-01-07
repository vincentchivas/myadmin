# -*- coding: utf-8 -*-
"""
@author: xshu
@date: 2014-07-15
@description: define the base model
"""

import logging
from provisionadmin import db
from provisionadmin.db.config import DBS
from provisionadmin.utils.common import now_timestamp


logger = logging.getLogger("model")


class ModelBase(dict):

    def __getattr__(self, name):
        return self[name] if name in self else None

    def __setattr__(self, name, value):
        self[name] = value
    # !!!

    def __delattr__(self, name):
        del self[name]

    @classmethod
    def check_required(cls, data):
        if not getattr(cls, 'required', None):
            return True
        for r in cls.required:
            if r not in data:
                return False
        return True

    @classmethod
    def check_unique(cls, data, extract=True):
        if extract:
            data = cls.extract(data)
        cond = cls.build_unique_cond(data)
        if not cond:
            return True
        if cls.find(cond, one=True):
            logger.warning("check unique fails with cond: %s", cond)
            return False
        return True

    @classmethod
    def build_unique_cond(cls, data):
        if not getattr(cls, 'unique', None):
            return
        cond = {}
        unique = cls.unique

        if len(unique) > 1:
            # unique should be tuple or list
            # like ("a", ("b", "c")) --->
            # {"or": [{"a": xx}, "$and": [{"b": yy}, {"c": zz}]]}
            or_cond = []
            for u in unique:
                if not isinstance(u, str):
                    and_cond = []
                    for ui in u:
                        if ui in data:
                            and_cond.append({ui: data[ui]})
                    or_cond.append({"$and": and_cond})
                else:
                    if u in data:
                        or_cond.append({u: data[u]})
            cond['$or'] = or_cond
        else:
            u = unique[0]
            if not isinstance(u, str):
                and_cond = []
                for ui in u:
                    if ui in data:
                        and_cond.append({ui: data[ui]})
                cond["$and"] = and_cond
            else:
                if u in data:
                    cond[u] = data[u]
        return cond

    @classmethod
    def extract(cls, data):
        ret_data = {}
        if hasattr(cls, 'required'):
            for r in cls.required:
                if r in data:
                    ret_data[r] = data[r]
                else:
                    return {}
        if hasattr(cls, 'optional'):
            for o in cls.optional:
                o_key = o[0]
                if o_key in data:
                    ret_data[o_key] = data[o_key]
                else:
                    if len(o) == 1:
                        continue
                    o_dv = o[1]
                    if callable(o_dv):
                        ret_data[o_key] = o_dv()
                    elif o_dv == "now_timestamp":
                        ret_data[o_key] = now_timestamp()
                    else:
                        ret_data[o_key] = o_dv
        return ret_data

    @classmethod
    def new(cls, data, extract=True):
        if extract:
            data = cls.extract(data)
        return cls(data)

    @classmethod
    def find(
            cls, cond={}, fields=None, id_only=False, one=False,
            toarray=False):
        _db = DBS[cls.db]
        if one:
            find = db.base_find_one
        else:
            find = db.base_find
        if id_only:
            fields = None
        if id_only or one:
            toarray = False
        info = find(_db, cls.collection, cond, fields, toarray)
        if id_only:
            if one:
                return info['_id'] if info else None
            else:
                return [i['_id'] for i in info]
        else:
            return info

    @classmethod
    def insert(cls, data, check_unique=True, get=False):
        data = cls.extract(data)
        if get:
            existed_item = cls.find(
                cls.build_unique_cond(data), one=True, id_only=True)
            if existed_item:
                return existed_item
        else:
            if not cls.check_unique(data, extract=False):
                logger.warning("check unique fails for data: %s", data)
                return "unique_failed"
        print data
        return db.base_insert(DBS[cls.db], cls.collection, data)
        # return generated _id

    @classmethod
    def update(cls, cond, data, replace=False, multi=False):
        db.base_update(
            DBS[cls.db], cls.collection, cond, data,
            replace=replace, multi=multi)
        # DBS[cls.db][cls.collection].update(cond, data)

    @classmethod
    def remove(cls, cond):
        db.base_remove(DBS[cls.db], cls.collection, cond)

    @classmethod
    def save(cls, data, check_unique=False, extract=False):
        if extract:
            data = cls.extract(data)
            logger.info("data %s" % data)
        if check_unique:
            cls.check_unique(data, extract=False)
            logger.warning("check unique failed for data: %s" % data)
            return 'unique-error'
        return db.base_save(DBS[cls.db], cls.collection, data)

    @classmethod
    def find_id_by_unique(cls, cond=None, data=None):
        if cond is None:
            cond = {}
            if data is None:
                logger.warning("both data and cond is None")
                return None
            for u in cls.unique:
                if not isinstance(u, str):
                    for ui in u:
                        if ui not in data:
                            cond = {}
                            break
                        else:
                            cond[ui] = data[ui]
                    else:
                        break
                else:
                    if u in data:
                        cond[u] = data[u]
                        break
            if not cond:
                logger.warning("can not build unique cond from data")
                return None
        return cls.find(cond, id_only=True, one=True)
