# -*- coding: utf-8 -*-
import logging
from provisionadmin.db.config import USER_DB
from provisionadmin.model.user import Permission

_LOGGER = logging.getLogger('user')


def find_session(filters={}):
    item = USER_DB.sessions.find_one(filters)
    return item


def _get_app_container(appid):
    ret = {}
    filters = {"id": appid}
    try:
        app = USER_DB.apps.find_one(filters)
        ret["app_label"] = app.get("app_name")
        if app.get("type") == 1:
            ret["container"] = app.get("app_name")
        else:
            ret["container"] = app.get("container_name")
    except Exception, exception:
        _LOGGER.info("_get_app_container except occurred:%s" % str(exception))
    return ret


def _check_perm_exist(perm_name):
    filters = {"perm_name": perm_name}
    try:
        perm = USER_DB.permission.find_one(filters)
    except Exception, exception:
        _LOGGER.info("_check_perm_exist except occurred:%s" % str(exception))
    if perm:
        return True
    else:
        return False


def init_perms():
    count = 0
    models = USER_DB.models.find()
    for model in models:
        appid = model.get("app_id")
        app_cont = _get_app_container(appid)
        for operator in model.get("actions"):
            perm = Permission()
            perm.model_label = model.get("model_name")
            perm.perm_type = "model"
            perm.app_label = app_cont.get("app_label")
            perm.container = app_cont.get("container")
            perm.action = operator
            perm.perm_name = perm.app_label + "-" + perm.model_label + "-" + \
                perm.action
            if not _check_perm_exist(perm.perm_name):
                Permission.save_perm(perm)
                count = count + 1
    return count
