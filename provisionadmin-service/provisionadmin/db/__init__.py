"""
@author: zhhfang
@date: 2014-07-15
@description: define the base operation of mongodb
"""

import logging
import provisionadmin.db.models
from provisionadmin.db.seqid import get_next_id
# to trigger the db init action

logger = logging.getLogger("db")


def base_insert(db, coll, data):
    logger.info("@base_insert --- coll: %s; data: %s", coll, data)
    # to avoid _id error
    data.pop('_id', None)
    if not data.get("id"):
        data["id"] = get_next_id(coll)
    db[coll].insert(data)
    return data["id"]


def base_save(db, coll, data):
    logger.info("@base_save --- coll: %s; data: %s", coll, data)
    if not data.get('_id'):
        data["_id"] = get_next_id(coll)
    return db[coll].save(data)


def base_update(db, coll, cond, data, replace=False, multi=False):
    logger.info(
        "@base_update --- coll: %s; cond: %s; data: %s: ",
        coll, cond, data)
    if not replace:
        # to avoid _id error
        data.pop('_id', None)
        data = {'$set': data}
    else:
        data['$set'].pop('_id', None)
    return db[coll].update(cond, data, multi=multi)


def base_find_one(db, coll, cond, fields, toarray=False):
    logger.info(
        "@base_find_one --- coll: %s; cond: %s; fields: %s, toarray: %s;",
        coll, cond, fields, toarray)
    if fields:
        return db[coll].find_one(cond, fields=fields)
    else:
        return db[coll].find_one(cond)


def base_find(db, coll, cond, fields, toarray=False):
    logger.info(
        "@base_find --- coll: %s; cond: %s; fields: %s, toarray: %s;",
        coll, cond, fields, toarray)
    if fields:
        cursor = db[coll].find(cond, fields)
    else:
        cursor = db[coll].find(cond)
    if toarray:
        return [i for i in cursor]
    else:
        return cursor


def base_remove(db, coll, cond):
    logger.info("@base_remove --- coll: %s; cond: %s", coll, cond)
    db[coll].remove(cond)
