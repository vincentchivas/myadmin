# -*- coding: utf-8 -*-

from django.http import HttpResponse
# from django.conf import settings
import logging
# from django.http import HttpResponse
from django.conf import settings
from provisionadmin.model.user import User, Permission, UserLog
from provisionadmin.utils import json, respcode, exception
from provisionadmin.utils.perm_list import Perm_Sys


EXCEPTION_DEBUG = settings.EXCEPTION_DEBUG and settings.DEBUG
AUTH_DEBUG = settings.DEBUG and settings.AUTH_DEBUG
_LOGGER = logging.getLogger('provisionadmin')

EXCEPTION_CODE_PAIRS = (
    (respcode.AUTH_ERROR, exception.AuthFailureError,),
    (respcode.DB_ERROR, exception.DbError,),
    (respcode.DATA_ERROR, exception.DataError,),
    (respcode.DATA_ERROR, exception.UniqueCheckError,),
    (respcode.PARAM_ERROR, exception.ParamsError,),
    (respcode.IO_ERROR, IOError,),
    (respcode.UNKNOWN_ERROR, exception.UnknownError,),
)


def _get_respcode_of_exception(e):
    e_type = type(e)
    for code, exception_type in EXCEPTION_CODE_PAIRS:
        if e_type == exception_type:
            return code
    else:
        return respcode.UNKNOWN_ERROR


def exception_handler(as_json=True):
    """
    catch the exception and return specified respcode
    """
    def e_wrapper(func):
        def wrapper(request, *args, **kwargs):
            try:
                if request.method == 'OPTIONS':
                    return json.json_response_ok({}, 'can cross-domain')
                return func(request, *args, **kwargs)
            except Exception as e:
                _LOGGER.exception(e)
                if EXCEPTION_DEBUG:
                    raise e
                else:
                    if as_json:
                        return json.json_response_error(
                            _get_respcode_of_exception(e), {}, e.message)
                    else:
                        return HttpResponse(e.message)
        return wrapper
    return e_wrapper


def _check_has_perm(uid, perm_name_list):
    assert perm_name_list
    perm_names = []
    perms_model = Permission.get_perms_by_uid(uid)
    # default get the user's permissions of the type "model"
    if perms_model:
        for perm in perms_model:
            perm_names.append(perm.get("perm_name"))
        perms_feature = Permission.init_features(uid)
        perm_names = perm_names + perms_feature
        if set(perm_name_list) < set(perm_names):
            return True
        else:
            return False
    else:
        return False


def _save_to_log(usr, perms):
    assert perms
    for perm in perms:
        uid = usr.get("_id")
        uname = usr.get("user_name")
        log = UserLog.new(uid, uname, perm)
        UserLog.save_log(log)


def check_session(func):
    '''
    check user session
    '''
    def wrapper(req, *args, **kv):
        check = False
        uid = req.session.get('uid')
        try:
            uid = int(uid)
        except Exception as e:
            _LOGGER.exception(e)
            return json.json_response_error(respcode.AUTH_ERROR, {}, e.message)
        if uid:
            usr = User.find_one_user({'_id': uid})
            kv.update({'user': usr})
            _LOGGER.info("user %s check_session" % usr.get("user_name"))
            if not usr.get("group_id"):
                return json.json_response_error(
                    respcode.AUTH_ERROR,
                    {}, "the user has no roles,please check")
            if usr.get("is_active"):
                    # to check the user has the permission
                    # add the operator the user will do
                req_method = req.method
                func_name = func.__name__
                module_name = func.__module__
                last_name = module_name.split('.')[-1]
                api_name = last_name + "_" + func_name
                if hasattr(Perm_Sys, api_name):
                    perms_dict = getattr(Perm_Sys, api_name)
                    perm_names_list = perms_dict.get(req_method)
                    check = _check_has_perm(uid, perm_names_list)
                    _LOGGER.info(
                        "user %s perms_check" % usr.get("user_name"))
                    if check:
                        _save_to_log(usr, perm_names_list)
        if check or AUTH_DEBUG:
            return func(req, *args, **kv)
        else:
            return json.json_response_error(
                respcode.AUTH_ERROR, {}, 'auth error')
    return wrapper
