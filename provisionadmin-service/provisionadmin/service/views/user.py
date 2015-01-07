# -*- coding: utf-8 -*-
import simplejson
import time
import logging
from provisionadmin.model.user import User, Group, Permission, UserLog
from provisionadmin.decorator import check_session, exception_handler
from provisionadmin.utils.json import json_response_error, json_response_ok
from provisionadmin.utils import respcode
from provisionadmin.utils.common import unixto_string, now_timestamp

_LOGGER = logging.getLogger("view")


@exception_handler()
def login(req):
    '''
    login api is used for user to login in the system
    and return the left navigation and permissions

    Request URL: admin/login

    HTTP Method: POST

    Parameters:
     --user_name:user name to login
     --password:

    Return:
    {
     "status":0
     "data":{
              "features":["aa","bb"] ,
              "menu":{"items":[{"display":"Translation","model":"translate"}]},
              "permissions":[{"action":"add","model":"translation"}]
            }
        }
    '''

    if req.method == 'POST':
        temp_strs = req.raw_post_data
        try:
            temp_dict = simplejson.loads(temp_strs)
            print temp_dict
        except ValueError as e:
            _LOGGER.info(e)
        name = req.POST.get('user_name')
        if not name:
            name = temp_dict.get("user_name")
        password = req.POST.get('password')
        if not password:
            password = temp_dict.get("password")
        if name and password:
            user_check = User.find_one_user(
                {'user_name': name, 'password': password})
            if not user_check:
                return json_response_error(
                    respcode.AUTH_ERROR, {},
                    msg='Look like that is not right. Give it another try?')
            else:
                if user_check.get("is_active"):
                    req.session["uid"] = user_check['_id']
                    uid = int(user_check['_id'])
                    upt_dict = {
                        "last_login": now_timestamp(),
                        "total_login": user_check.get("total_login") + 1}
                    User.update_user({"_id": uid}, upt_dict)
                    permissions = Permission.init_menu(uid)
                    return json_response_ok(
                        data=permissions, msg='get left navi menu')
                else:
                    return json_response_error(
                        respcode.AUTH_ERROR, {},
                        msg='This account is not actived.')
        else:
            return json_response_error(
                respcode.PARAM_REQUIRED,
                msg='user_name or password is not allowed  empty')
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method wrong")


@exception_handler()
@check_session
def logout(req):
    # session_key = req.session.session_key
    req.session.delete()
    return json_response_ok(data={}, msg='logout success')


@exception_handler()
def change_password(req):
    if req.method == 'POST':
        old_pwd = req.POST.get('old_pwd')
        new_pwd = req.POST.get('new_pwd')
        uid = req.session["uid"]
        usr = User.find_one_user({'_id': uid})
        if usr:
            if usr.get("password") == old_pwd:
                User.update_user({"_id": uid}, {"password": new_pwd})
                return json_response_ok(data={}, msg='password changed')
            else:
                return json_response_error(
                    respcode.PASSWORD_UNMATCH, data={},
                    msg='old password is not match')
    else:
        return json_response_error(
            respcode.METHOD_ERROR, data={},
            msg='http request method error')


@exception_handler()
def list_group(req):
    '''
    list api for show group list.

    Request URL:  /auth/group/list

    Http Method:  GET

    Parameters : None

    Return :
    {
     "status":0
     "data":{
              "items":[
              {
              "_id":"2",
              "group_name":"admin",
              "permission_list":[19,20,21,22]
              },
              {
                "_id":4,
                "group_name":"translator",
                "permission_list":[22,23]
              }
              ]
            }
        }

    '''
    if req.method == 'GET':
        cond = {}
        raw_results = Group.find_group(cond)
        group_list = []
        for result in raw_results:
            group_dict = {"id": result.get("_id"),
                          "role_name": result.get("alias"),
                          "origin": result.get("alias")}
            group_list.append(group_dict)
        data = {}
        data.setdefault("items", group_list)
        return json_response_ok(data, "get group list")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def create_group(req):
    '''
    create api to add group.

    Request URL:  /auth/group/add

    Http Method:  POST

    Parameters:
        {
           "group_name":"xxx",
           "perm_list":[1,2,3,4]
        }

    Return :
    {
     "status":0
     "data":{}
     "msg":"add successfully"
    }
    '''
    if req.method == 'POST':
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        group_name = temp_dict.get('rolename')
        if not group_name:
            return json_response_error(
                respcode.PARAM_REQUIRED,
                msg="parameter role_name invalid")
        group = Group.new(group_name, permission_list=[])
        group_id = Group.save_group(group)
        data = {}
        data["id"] = group_id
        data["role_name"] = group_name
        data["origin"] = group_name
        return json_response_ok(data, msg="add success")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg='http method error')


def _get_user_list(cond={}):
    users = []
    fields = {
        "user_name": 1,
        "group_id": 1,
        "department": 1,
        "is_active": 1,
        "last_login": 1,
        "total_login": 1,
        "mark": 1}
    raw_results = User.find_users(cond, fields)
    for user in raw_results:
        user["last_login"] = unixto_string(user.get("last_login"))
        user["id"] = user.get("_id")
        user.pop("_id")
        user["role"] = _get_group_name_list(user.get("group_id"))
        user.pop("group_id")
        user["group"] = user.pop("department", None)
        users.append(user)
    return users


def detail_modify_group(req, group_id):
    '''
    this api is used to view or modify one group

    Request URL: /auth/group/{gid}

    HTTP Method:GET
    Parameters: None
    Return
     {
     "status":0
     "data":{
              "item":[
              {
              "_id":"2",
              "group_name":"admin",
              "permission_list":[19,20,21,22]
              }
            }
        }

    HTTP Method:POST
    Parameters:
        {
           "group_name":"xxx",
           "perm_list":[1,2,3,4]
        }
    Return :
     {
     "status":0
     "data":{}
     "msg":"modify successfully"
    }
    '''
    group_id = int(group_id)
    if req.method == "GET":
        cond = {"_id": group_id}
        groups = Group.find_group(cond)
        if groups:
            data = {}
            users = _get_user_list(cond={"group_id": group_id})
            data.setdefault("items", users)
            return json_response_ok(
                data, msg="get group one group detail")
        else:
            return json_response_error(
                respcode.PARAM_ERROR, msg="the id is not exist")
    elif req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        group_name = temp_dict.get('role_name')
        if not group_name:
            return json_response_error(
                respcode.PARAM_REQUIRED,
                msg="parameter group_name invalid")
        cond = {"_id": group_id}
        upt_dict = {"alias": group_name}
        Group.update_group(cond, upt_dict)
        data = {}
        data["id"] = group_id
        data["role_name"] = group_name
        data["origin"] = group_name
        return json_response_ok(data, msg='update success')
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def delete_group(req):
    '''
    this api is used to delete group,when one group removed,the user who
    in this group ,the group id will remove too.

    Request URL: /auth/group/delete

    HTTP Method: POST

    Parameters:
        {
            "gids":[2,3]
            }

    Return:
     {
     "status":0
     "data":{}
     "msg":"delete successfully"
     }
    '''
    if req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        gids = temp_dict.get("gids")
        assert gids
        ids = Group.del_group(gids)
        if not ids:
            return json_response_ok({}, msg="delete successfully")
        else:
            return json_response_error(
                respcode.PARAM_ERROR, msg="ids:%s is invalid" % ids)
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def _get_group_list_by_ids(array=[]):
    role_list = []
    if not array:
        return []
    else:
        for gid in array:
            groups = Group.find_group({"_id": gid})
            group = groups[0]
            role_dict = {"display_value": group.get("alias"),
                         "value": group.get("group_name"),
                         "selected": True}
            role_list.append(role_dict)
        return role_list


def _get_group_name_list(array=[]):
    name_list = []
    if not array:
        return []
    else:
        for gid in array:
            groups = Group.find_group({"_id": gid})
            group = groups[0]
            name_list.append(group.get("group_name"))
        return name_list


def _get_group_ids(name_list):
    gids = []
    if not name_list:
        return []
    else:
        for name in name_list:
            groups = Group.find_group({"group_name": name})
            gids.append(groups[0].get("_id"))
        return gids


def list_user(req):
    '''
        list api for show user list.

        Request URL:  /auth/user/list

        Http Method:  GET

        Parameters : None

        Return :
        {
        "status":0
        "data":{
                "items":[
                {
                "_id":"2",
                "user_name":"admin",
                "email":"xx@bainainfo.com",
                "permission_list":[19,20,21,22]
                },
                {
                    "_id":4,
                    "user_name":"translator",
                    "email":"xx@bainainfo.com",
                    "permission_list":[22,23]
                }
                ]
                }
            }

        '''
    if req.method == 'GET':
        users = _get_user_list()
        data = {}
        data.setdefault("items", users)
        # filters = User.get_filters()
        groups_roles = User.get_groups_roles(filters=True)
        items_dict = {}
        items_dict["groups"] = groups_roles[0]
        items_dict["roles"] = groups_roles[1]
        data["filters"] = items_dict
        return json_response_ok(data, "get user list")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def create_user(req):
    '''
        create api to add user.

        Request URL:  /auth/user/add

        Http Method:  POST

        Parameters:
            {
            "user_name":"zxy@bainainfo.com",
            "group_id":[1],
            "mark":"new user",
            "department":"server"
            }

        Return :
        {
        "status":0,
        "data":{},
        "msg":"add successfully"
        }
        '''
    if req.method == 'POST':
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        required_list = ('user_name',)
        for required_para in required_list:
            if not temp_dict.get(required_para):
                return json_response_error(
                    respcode.PARAM_REQUIRED,
                    msg="parameter %s invalid" % required_para)
        user_name = temp_dict.get('user_name')
        if User.find_one_user({"user_name": user_name}):
            return json_response_error(
                respcode.PARAM_REQUIRED,
                msg="the email has been used!")
        group_names = temp_dict.get('roles')
        password = User.calc_password_hash("123456")
        group_id = _get_group_ids(group_names)
        department = temp_dict.get('groups')
        mark = temp_dict.get('mark')
        user_instance = User.new(user_name, password)
        user_instance.group_id = group_id
        user_instance.department = department
        user_instance.mark = mark
        User.save(user_instance)
        return json_response_ok({"info": user_instance})
    elif req.method == 'GET':
        data = {}
        groups_roles = User.get_groups_roles()
        data["groups"] = groups_roles[0]
        data["roles"] = groups_roles[1]
        # data["departments"] = User.get_departments()
        return json_response_ok(data, "get departments")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg='http method error')


def detail_modify_user(req, user_id):
    '''
        this api is used to view or modify one user

        Request URL: /auth/user/{uid}

        HTTP Method:GET
        Parameters: None
        Return
        {
        "status":0
        "data":{
                "item":[
                {
                "_id":"2",
                "user_name":"xxx",
                "permission_list":[19,20,21,22]
                }
                }
            }

        HTTP Method:POST
        Parameters:
            {
            "group_name":"xxx",
            "perm_list":[1,2,3,4]
            }
        Return :
        {
        "status":0
        "data":{}
        "msg":"modify successfully"
        }
        '''
    user_id = int(user_id)
    if req.method == "GET":
        cond = {"_id": user_id}
        fields = {
            "user_name": 1,
            "group_id": 1,
            "department": 1,
            "mark": 1}
        raw_result = User.find_users(cond, fields)
        if raw_result:
            user = raw_result[0]
            user["id"] = user.get("_id")
            user.pop("_id")
            user["roles"] = _get_group_list_by_ids(user.get("group_id"))
            data = {}
            group_id_list = user.get("group_id")
            user.pop("group_id")
            groups_roles = User.get_groups_roles(
                user.get("department"), group_id_list)
            data["groups"] = groups_roles[0]
            data["roles"] = groups_roles[1]
            # data["departments"] = User.get_departments(
            #     user.get("department"), group_id_list)
            data.setdefault("user", user)
            return json_response_ok(
                data, msg="get  one user detail")
        else:
            return json_response_error(
                respcode.PARAM_ERROR, msg="the user is not exist")
    elif req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        required_list = ('user_name',)
        for required_para in required_list:
            if not temp_dict.get(required_para):
                return json_response_error(
                    respcode.PARAM_REQUIRED,
                    msg="parameter %s invalid" % required_para)
        user_name = temp_dict.get('user_name')
        group_names = temp_dict.get('roles')
        group_id = _get_group_ids(group_names)
        department = temp_dict.get('groups')
        mark = temp_dict.get('mark')
        cond = {"_id": user_id}
        upt_dict = {"user_name": user_name,
                    "group_id": group_id,
                    "department": department,
                    "mark": mark}
        User.update_user(cond, upt_dict)
        return json_response_ok({'info': "save use info successfully"})
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def delete_user(req):
    '''
        this api is used to delete user.

        Request URL: /auth/user/delete

        HTTP Method: POST

        Parameters:
            {
                "uids":[2,3]
                }

        Return:
        {
        "status":0
        "data":{}
        "msg":"delete successfully"
        }
    '''
    if req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        uids = temp_dict.get("uids")
        assert uids
        ids = User.del_user(uids)
        if not ids:
            return json_response_ok({}, msg="delete successfully")
        else:
            return json_response_error(
                respcode.PARAM_ERROR, msg="ids:%s is invalid" % ids)
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def list_perm(req):
    '''
    list api for show user perm.

    Request URL:  /auth/perm/list

    Http Method:  GET

    Parameters : None

    Return :
    {
    "status":0
    "data":{
            "items":[
            {
                "_id":"2",
                "app_label":"translations-tool",
                "model_label":"translations",
                "operator":"add"
            },
            {
                "_id":4,
                "app_label":"translator-tool",
                "model_label":"revsion",
                "operator":"list"
            }
            ]
            }
        }

    '''
    if req.method == 'GET':
        cond = {}
        perms = Permission.find_perm(cond)
        data = {}
        data.setdefault("items", perms)
        return json_response_ok(data, "get permission list")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def user_active(req):
    if req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        uid = temp_dict.get("id")
        status = temp_dict.get("is_active")
        User.update_user(
            {"_id": uid}, {"is_active": status})
        return json_response_ok({}, msg="update active success")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def group_perm_list(req):
    if req.method == "GET":
        grant_id = req.GET.get("roleid")
        uid = req.session["uid"]
        models = Permission.user_perm_list(uid, group_id=int(grant_id))
        features = Permission.user_perm_feature(uid, group_id=int(grant_id))
        data = {}
        feature_dict = {}
        feature_dict["title"] = "Feature"
        feature_dict["items"] = features
        data["feature"] = feature_dict
        data["items"] = models
        return json_response_ok(data, "get group perm list")
    elif req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        gid = temp_dict.get("roleid")
        perm_list = temp_dict.get("permissions")
        Group.update_group(
            {"_id": gid}, {"permission_list": perm_list})
        return json_response_ok({}, "grant group perm list")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def user_perm_list(req):
    if req.method == "GET":
        grant_id = req.GET.get("userid")
        uid = req.session["uid"]
        models = Permission.user_perm_list(uid, grant_id=int(grant_id))
        features = Permission.user_perm_feature(uid, grant_id=int(grant_id))
        data = {}
        feature_dict = {}
        feature_dict["title"] = "Feature"
        feature_dict["items"] = features
        data["feature"] = feature_dict
        data["items"] = models
        return json_response_ok(data, "get user perm list")
    elif req.method == "POST":
        temp_strs = req.raw_post_data
        temp_dict = simplejson.loads(temp_strs)
        uid = temp_dict.get("userid")
        perm_list = temp_dict.get("permissions")
        User.update_user(
            {"_id": uid}, {"permission_list": perm_list})
        return json_response_ok({}, msg="grant user perm list")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")


def action_log_list(req):
    if req.method == "GET":
        department = req.GET.get("group")
        group_name = req.GET.get("role")
        start_time = req.GET.get("start")
        start = time.mktime(time.strptime(start_time, '%Y-%m-%d'))
        one_day = 86400.0
        end_time = req.GET.get("end")
        end = time.mktime(time.strptime(end_time, '%Y-%m-%d')) + one_day
        cond = {"modified": {"$gte": start, "$lte": end}}
        # when the department is empty and group_name is empty
        if department is not None or group_name is not None:
            user_name = req.GET.get("user_name")
            find_list = UserLog.search_log_info(cond)
            raw_results = find_list.sort('modified', -1)
            cond_for_users = {}
            logs = []
            if user_name:
                cond_for_users["user_name"] = {"$regex": user_name}
            if group_name:
                group = Group.find_group({"group_name": group_name})[0]
                group_id = group.get("_id")
                cond_for_users["group_id"] = group_id
            if department:
                cond_for_users["department"] = department
            user_list = []
            raw_user_list = User.find_users(
                cond_for_users, {"user_name": 1, "_id": 0})
            for user in raw_user_list:
                user_list.append(user.get("user_name"))
            for result in raw_results:
                if result.get("user_name") in user_list:
                    log_dict = {}
                    log_dict["time"] = unixto_string(result.get("modified"))
                    log_dict["id"] = result.get("_id")
                    log_dict["actions"] = result.get(
                        "perm_name").replace('-', ' ')
                    log_dict["user_name"] = result.get("user_name")
                    logs.append(log_dict)
            data = {}
            data["items"] = logs
            return json_response_ok(data, "filter user log")
        else:
            find_list = UserLog.search_log_info(cond)
            raw_results = find_list.sort('modified', -1)
            logs = []
            for result in raw_results:
                log_dict = {}
                log_dict["time"] = unixto_string(result.get("modified"))
                log_dict["id"] = result.get("_id")
                log_dict["actions"] = result.get("perm_name").replace('-', ' ')
                log_dict["user_name"] = result.get("user_name")
                logs.append(log_dict)
            data = {}
            data["items"] = logs
            groups_roles = User.get_groups_roles(filters=True)
            items_dict = {}
            items_dict["groups"] = groups_roles[0]
            items_dict["roles"] = groups_roles[1]
            data["filters"] = items_dict
            return json_response_ok(data, "get user log")
    else:
        return json_response_error(
            respcode.METHOD_ERROR, msg="http method error")
