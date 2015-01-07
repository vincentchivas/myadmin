# -*- coding: utf-8 -*-
import logging
import os
import errno
import shutil
import simplejson
import time
import re

from PIL import Image
from django.conf import settings
from provisionadmin.utils.json import json_response_error, json_response_ok
from provisionadmin.decorator import exception_handler
from provisionadmin.model.preset import classing_model
from provisionadmin.utils.respcode import (
    PARAM_ERROR, METHOD_ERROR, PARAM_REQUIRED, DATA_ERROR,
    ONLINE_DATA_UNDELETE, DATA_RELETED_BY_OTHER, DUPLICATE_DELETE)
from provisionadmin.utils.common import now_timestamp, unixto_string
from provisionadmin.utils import scp

_LOGGER = logging.getLogger("view")
_RESOURCE_BASE_DIR = "preset_icon/"
_PLATFORM_INFO = {"ios": "IOS", "android": "Android"}
DB_SERVERS = settings.REMOTEDB_SETTINGS
S3_DOMAIN = settings.S3_DOMAIN
HOST = settings.HOST
MEDIA_ROOT = settings.MEDIA_ROOT
PAGE_SIZE = 20
_ONE_DAY = 86400.0
_PIC_TYPES = ['png', 'jpg', "gif", "jpeg", "bmp"]
ICON_TAG_RE = r'^(http://.*/resources/)(.*)'
icon_tag_compile = re.compile(ICON_TAG_RE, re.S)


@exception_handler()
def preset_icon_list(request):
    """
    GET: Show icon list
    Parameters:
        -None
    Return:
        -1. the list of icon
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == "GET":
        Icon = classing_model("icon")
        if hasattr(Icon, "list_api"):
            list_api = Icon.list_api
        else:
            return json_response_error(
                PARAM_ERROR, msg="list_api is not configed")
        fields = list_api["fields"]
        if list_api.get("search_fields"):
            search_fields = list_api["search_fields"]
        page = int(request.GET.get("index", 1)) - 1
        page_size = int(request.GET.get("limit", 20))
        data = {}
        data["filters"] = _get_list_filter()
        cond = _icon_query_condition(request, search_fields)

        sort = [("last_modified", -1)]
        data["items"], data["total"] = _get_list(
            Icon, cond, fields, sort, page, page_size)
        return json_response_ok(data)
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


@exception_handler()
def get_icon_display_data(request):
    """
    GET: Get icon display data
    Parameters:
        -None
    Return:
        -1. the list of icon display data
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == "GET":

        data = {}
        data["platform"] = _get_platform_info()
        return json_response_ok(data)
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


@exception_handler()
def preset_add_icon(request):
    """
    POST: Save the resource of document
    Parameters:
        -icon: the name of icon file,
        -title: the tile of icon
        -category: the category of icon
    Return:
        -1. upload success
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == 'POST':
        Icon = classing_model("icon")

        iconfile = request.FILES.get('icon')
        if not iconfile:
            return json_response_error(
                PARAM_REQUIRED, msg="parameter 'icon' invalid")
        required_list = ("title", "category", "type", "platform", "package")
        for required_para in required_list:
            if request.POST.get(required_para) is None:
                return json_response_error(
                    PARAM_REQUIRED,
                    msg="parameter %s request" % required_para)

        iconfile = request.FILES['icon']
        icon_name = iconfile.name.lower()

        icon_suffix = icon_name.split('.')[-1]

        if icon_suffix not in _PIC_TYPES:
            return json_response_error(
                DATA_ERROR, msg='upload file format error[%s]' % (icon_name))

        resource = {}
        temp_dict = request.POST
        resource["platform"] = temp_dict.get("platform").lower()
        resource["package"] = simplejson.loads(temp_dict.get("package"))
        resource["title"] = temp_dict.get("title")
        resource["type"] = simplejson.loads(temp_dict.get("type"))
        resource["category"] = simplejson.loads(temp_dict.get("category"))
        cur_time = now_timestamp()
        icon_name = "%s.%s" % (cur_time, icon_suffix)
        resource["icon"] = _RESOURCE_BASE_DIR + icon_name

        # check package name in db
        Aospackage = classing_model("aospackage")
        for i in resource["package"]:
            cond = {"id": int(i)}
            aospackage_info = Aospackage.find(cond, one=True)
            if not aospackage_info:
                return json_response_error(DATA_ERROR, msg="no package in db")

        # get icon file height and width and save icon to resource path
        resource["height"], resource["width"] = _save_icon_file(iconfile)

        resource["last_modified"] = now_timestamp()

        # save pic information to MongoDB
        result = Icon.insert(resource)
        if result == "unique_failed":
            return json_response_error(
                PARAM_ERROR,
                msg="unique check failed")
        return json_response_ok({}, msg="add icon success")
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


@exception_handler()
def preset_edit_icon(request):
    """
    POST: Modify the resource of document
    Parameters:
        -id: the id of icon,
        -icon: the name of icon file,
        -title: the tile of icon
        -category: the category of icon
    Return:
        -1. modify success
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == "GET":
        required_list = ("id",)
        for required_para in required_list:
            if request.GET.get(required_para) is None:
                return json_response_error(
                    PARAM_REQUIRED,
                    msg="parameter %s request" % required_para)
        Icon = classing_model("icon")

        icon_id = int(request.GET.get("id"))
        cond = {}
        cond["id"] = icon_id
        fields = {
            "_id": 0, "upload_ec2": 0, "upload_china": 0, "upload_local": 0,
            "memo": 0, "modified_time": 0, "created_time": 0}
        icon_info = Icon.find(cond, fields, one=True)
        if not icon_info:
            return json_response_error(DATA_ERROR, msg="no icon in db")
        if icon_info.get("icon"):
            icon_info["icon"] = "http://%s/admin/media/%s" % (
                HOST, icon_info['icon'])
        if icon_info.get("last_modified"):
            icon_info["last_modified"] = unixto_string(
                icon_info.get("last_modified"))
        data = icon_info
        return json_response_ok(data)
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


@exception_handler()
def preset_update_icon(request):
    """
    POST: Modify the resource of document
    Parameters:
        -id: the id of icon,
        -icon: the name of icon file,
        -title: the tile of icon
        -category: the category of icon
    Return:
        -1. modify success
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == 'POST':
        Icon = classing_model("icon")

        required_list = ("title", "platform")
        for required_para in required_list:
            if not request.POST.get(required_para):
                return json_response_error(
                    PARAM_REQUIRED,
                    msg="parameter %s request" % required_para)
        other_required_list = ("category", "type", "package")
        for required_para in other_required_list:
            if not simplejson.loads(request.POST.get(required_para)):
                return json_response_error(
                    PARAM_REQUIRED,
                    msg="parameter %s request" % required_para)

        iconfile = request.FILES.get('icon')
        if iconfile:
            icon_name = iconfile.name.lower()
            icon_suffix = icon_name.split('.')[-1]

            if icon_suffix not in _PIC_TYPES:
                return json_response_error(
                    DATA_ERROR,
                    msg='upload file format error[%s]' % (icon_name))

        icon_id = int(request.POST.get("id"))

        cond = {}
        cond["id"] = icon_id
        icon_info = Icon.find(cond, one=True)
        if not icon_info:
            return json_response_error(DATA_ERROR, msg="no icon in db")

        icon_info["last_modified"] = now_timestamp()
        icon_info["platform"] = request.POST.get("platform").lower()
        icon_info["package"] = simplejson.loads(request.POST.get("package"))
        icon_info["title"] = request.POST.get("title")
        icon_info["type"] = simplejson.loads(request.POST.get("type"))
        icon_info["category"] = simplejson.loads(request.POST.get("category"))

        if iconfile:
            # remove old  icon file
            old_icon_file = icon_info.get("icon")
            if old_icon_file:
                old_icon_file_path = os.path.join(MEDIA_ROOT, old_icon_file)
                if os.path.exists(old_icon_file_path):
                    os.remove(old_icon_file_path)

            icon_name = iconfile.name.lower()
            icon_suffix = icon_name.split('.')[-1]
            cur_time = now_timestamp()
            icon_name = "%s.%s" % (cur_time, icon_suffix)
            icon_info["icon"] = _RESOURCE_BASE_DIR + icon_name

            # get icon file height and width and save icon to resource path
            icon_info["height"], icon_info["width"] = _save_icon_file(iconfile)

        # update icon information in MongoDB
        result = Icon.find({"title": icon_info["title"]}, one=True)
        if result:
            if result["id"] != icon_id:
                return json_response_error(
                    PARAM_ERROR, msg="unique check failed")
        Icon.update(cond, icon_info)
        _LOGGER.info("the id:%s is update successful", icon_id)
        return json_response_ok({}, msg="update icon success")
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


@exception_handler()
def preset_upload_icon(request):
    """
    POST: upload resource to server
    Parameters:
        -id: the id of icon,
    Return:
        -1. upload success
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == 'POST':
        temp_strs = request.raw_post_data
        try:
            temp_dict = simplejson.loads(temp_strs)
        except ValueError as expt:
            _LOGGER.error("upload icon api para except:%s", expt)
            return json_response_error(
                PARAM_ERROR,
                msg="json loads error,check parameters format")
        required_list = ("server", "items")
        for required_para in required_list:
            if temp_dict.get(required_para) is None:
                return json_response_error(
                    PARAM_REQUIRED,
                    msg="parameter %s request" % required_para)
        server = temp_dict.get("server", "local")
        icon_info = temp_dict.get("items")
        data = {}
        result = _update_icon_info(icon_info, server, is_del=False)
        data["upload_success"] = result[0]
        if result[1]:
            data["upload_failed"] = result[1]
            return json_response_error(DATA_ERROR, data)
        else:
            data["upload_failed"] = []
            return json_response_ok(data)
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


@exception_handler()
def preset_delete_icon(request):
    """
    POST: delete resource from server
    Parameters:
        -id: the id of icon,
    Return:
        -1. upload success
            {
                "status": 0,
                "data":{
                       ...
                }
            }
        -2. error http method
            {
                "status": 11,
                "data":{
                       ...
                }
            }
    """
    if request.method == 'POST':
        temp_strs = request.raw_post_data
        try:
            temp_dict = simplejson.loads(temp_strs)
        except ValueError as expt:
            _LOGGER.error("delete icon api para except:%s", expt)
            return json_response_error(
                PARAM_ERROR,
                msg="json loads error,check parameters format")
        required_list = ("server", "items")
        for required_para in required_list:
            if temp_dict.get(required_para) is None:
                return json_response_error(
                    PARAM_REQUIRED,
                    msg="parameter %s request" % required_para)
        server = temp_dict.get("server", "local")
        icon_info = temp_dict.get("items")
        data = {}
        if server == "admin":
            result = _delete_icon_from_admin(icon_info)
            data["delete_success"] = result[0]
            if result[1]:
                data["delete_failed"] = result[1]
                return json_response_error(ONLINE_DATA_UNDELETE, data)
            elif result[2]:
                data["delete_failed"] = result[2]
                return json_response_error(DATA_RELETED_BY_OTHER, data)
            else:
                data["delete_failed"] = []
                return json_response_ok(data)
        else:
            result = _update_icon_info(icon_info, server, is_del=True)
            data["delete_success"] = result[0]
            if result[1]:
                data["delete_failed"] = result[1]
                return json_response_error(DATA_ERROR, data)
            elif result[2]:
                data["delete_failed"] = result[2]
                return json_response_error(DUPLICATE_DELETE, data)
            else:
                data["delete_failed"] = []
                return json_response_ok(data)
    else:
        return json_response_error(METHOD_ERROR, msg="http method wrong")


def _get_list(model, cond, fields, sort=None, page=0, page_size=PAGE_SIZE):
    '''
    Get array data of specified collection.
    '''
    icon_info = []
    result_cursor = model.find(cond, fields=fields)
    if sort is not None:
        result_cursor = result_cursor.sort(sort)
    result_cursor = result_cursor.skip(
        page * page_size).limit(page_size)
    for i in result_cursor:
        if i:
            i["icon"] = "http://%s/admin/media/%s" % (HOST, i['icon'])
            icon_info.append(i)
    total = model.find(cond).count()
    return icon_info, total


def _save_icon_file(file_obj):
    # save pic file to resource path
    icon_name = file_obj.name.lower()
    cur_time = now_timestamp()
    icon_suffix = icon_name.split('.')[-1]
    new_icon_name = "%s.%s" % (cur_time, icon_suffix)
    resource_path = os.path.join(MEDIA_ROOT, _RESOURCE_BASE_DIR)
    if not os.path.exists(resource_path):
        os.makedirs(resource_path)
    iconfilepath = os.path.join(resource_path, new_icon_name)
    with open(iconfilepath, "wb") as picoutputfile:
        for chunk in file_obj.chunks():
            picoutputfile.write(chunk)

    # get icon file height and width
    try:
        image = Image.open(iconfilepath)
        height, width = image.size
    except:
        height, width = (0, 0)
    return height, width


def _get_list_filter():
    Icon = classing_model("icon")
    list_api = Icon.list_api
    filters = {"cascade": {}, "multi": []}
    platform_info = _get_platform_info()
    plat_default = {
        "display_value": u"选择平台", "value": "all", "children": {}}
    pack_default = {"display_value": u"项目名称", "value": "all"}
    plat_default["children"]["name"] = "package"
    plat_default["children"]["items"] = []
    plat_default["children"]['items'].append(pack_default)
    all_platform_info = platform_info["items"][0]["children"]["items"]
    plat_default["children"]['items'] += all_platform_info
    platform_info["items"].insert(0, plat_default)
    pack_default = {"display_value": u"项目名称", "value": "all"}
    platform_info["items"][1]["children"]["items"].insert(0, pack_default)
    filters["cascade"] = platform_info
    if list_api.get("filters"):
        filters["multi"] = list_api.get("filters")["multi"]
    return filters


def _get_platform_info():
    Aospackage = classing_model("aospackage")
    fields = {"id": 1, "title": 1}
    aospackage_info = Aospackage.find(
        cond={}, fields=fields, toarray=True)
    info = {"name": "platform", "items": []}
    platform_info = ["android"]
    for i in platform_info:
        plat_dict = {"display_value": "", "value": "", "children": {}}
        plat_dict["value"] = i
        plat_dict["display_value"] = _PLATFORM_INFO.get(i)

        plat_child = {"name": "package", "items": []}
        if i == "android":
            for j in aospackage_info:
                pack_items = {"display_value": "", "value": ""}
                pack_items["display_value"] = j["title"]
                pack_items["value"] = j["id"]
                plat_child["items"].append(pack_items)
        plat_dict["children"] = plat_child
        info["items"].append(plat_dict)
    return info


def _transfer_file(file_obj, server, is_del=False, from_s3=True):
    if file_obj and server:
        local_base = MEDIA_ROOT
        server_conf = DB_SERVERS[server]
        remote_base = server_conf['remote_base'] if server_conf.get(
            'remote') else '/home/static/resources'
        s3_flag = False
        if from_s3 and server_conf.get('s3_remote'):
            remote_base = server_conf["s3_remote"]
            s3_flag = True
        remote = os.path.join(remote_base, file_obj)
        if is_del:
            if s3_flag:
                try:
                    os.unlink(remote)
                    result = True
                except OSError as e:
                    result = False
            else:
                result = scp.sdel(
                    server_conf["statics"], 'static',
                    '/var/app/data/provisionadmin-service/static.pem', remote)
            return (result, "")
        else:
            local = os.path.join(local_base, file_obj)
            if s3_flag:
                try:
                    mkdir = os.path.dirname(remote)
                    os.makedirs(mkdir)
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise ValueError(
                            ('mkdir file path %s for s3 fail') % file_obj)
                try:
                    shutil.copy(local, remote)
                except EnvironmentError as e:
                    raise ValueError(('upload file %s to s3 fail') % file_obj)
                return (True, '%s/%s' % (S3_DOMAIN, file_obj))
            else:
                result = scp.scp(
                    server_conf['statics'], 'static',
                    '/var/app/data/provisionadmin-service/static.pem',
                    local, remote)
                if not result:
                    raise ValueError(('upload file %s fail') % file_obj)
                    return (False,)
                else:
                    return (
                        True, 'http://%s/resources/%s' % (
                            server_conf['domain'], file_obj))


def _delete_icon_from_admin(icon_info):
    Icon = classing_model("icon")
    success_results = []
    online_results = []
    refered_results = []
    for i in icon_info:
        cond = {}
        icon_id = int(i) if not isinstance(i, int) else i
        cond["id"] = icon_id
        icon_info = Icon.find(cond, one=True)
        if not icon_info:
            raise ValueError("icon:%s not in db", icon_id)
        if icon_info["refered_count"]:
            _LOGGER.error("icon:%s already refered", icon_info['title'])
            refered_results.append(icon_id)
            continue
        if icon_info["is_upload_local"] or icon_info["is_upload_ec2"]:
            online_results.append(icon_id)
            continue
        Icon.remove(cond)
        success_results.append(icon_id)
        # remove old  icon file
        old_icon_file = icon_info.get("icon")
        if old_icon_file:
            old_icon_file_path = os.path.join(MEDIA_ROOT, old_icon_file)
            if os.path.exists(old_icon_file_path):
                os.remove(old_icon_file_path)
    else:
        return success_results, online_results, refered_results


def _update_icon_info(icon_info, server, is_del=False):
    Icon = classing_model("icon")
    is_upload_server = "is_upload_%s" % server
    upload_server = "upload_%s" % server
    server_url = "%s_url" % server
    success_results = []
    failed_results = []
    duplicate_results = []
    for i in icon_info:
        cond = {}
        icon_id = int(i) if not isinstance(i, int) else i
        cond["id"] = icon_id
        fields = {"_id": 0}
        icon_info = Icon.find(cond, fields, one=True)
        is_upload = False
        if not icon_info:
            raise ValueError("icon:%s not in db", icon_info['title'])
        if is_del and not icon_info[is_upload_server]:
            _LOGGER.error("icon:%s already delete", icon_info['title'])
            duplicate_results.append(icon_info)
            continue
        file_obj = icon_info.get("icon")
        if not is_del and icon_info[is_upload_server]:
            is_upload = upload_iconfile(server, icon_info)
        if is_upload:
            icon_info["icon"] = "http://%s/admin/media/%s" % (
                HOST, icon_info['icon'])
            success_results.append(icon_info)
            continue

        result = _transfer_file(file_obj, server, is_del)
        if not result[0]:
            _LOGGER.error("operation:%s failed", icon_info['title'])
            icon_info["icon"] = "http://%s/admin/media/%s" % (
                HOST, icon_info['icon'])
            failed_results.append(icon_info)
            continue
        icon_info[is_upload_server] = False if is_del else True
        icon_info[server_url] = result[1]
        icon_info[upload_server] = now_timestamp()

        # update icon information in MongoDB
        Icon.update(cond, icon_info)
        _LOGGER.info("the id:%s is delete successful", icon_id)
        icon_info["icon"] = "http://%s/admin/media/%s" % (
            HOST, icon_info['icon'])
        success_results.append(icon_info)
    else:
        return success_results, failed_results, duplicate_results


def upload_iconfile(server, icon_info):
    """
    upload icon resource
    """
    server_url = "%s_url" % server
    file_obj = icon_info.get("icon")
    icon_url = icon_info.get(server_url)
    if icon_url:
        match_group = icon_tag_compile.match(icon_url)
        if not match_group:
            _LOGGER.warn('icon url not match regex![%s]' % icon_url)
            return False
        icon_file = match_group.group(2)
        if icon_file == file_obj:
            _LOGGER.info("icon:%s already upload", icon_info['title'])
            return True
        else:
            # remove old icon resource
            server_conf = DB_SERVERS[server]
            remote_base = server_conf['remote_base'] if server_conf.get(
                'remote') else '/home/static/resources'
            if icon_file:
                old_icon_file_path = os.path.join(remote_base, icon_file)
                if os.path.exists(old_icon_file_path):
                    os.remove(old_icon_file_path)
            return False


def derefered_icon(id):
    """
    deference icon resource
    """
    Icon = classing_model("icon")
    cond = {}
    icon_id = int(id) if not isinstance(id, int) else id
    cond["id"] = icon_id
    icon_info = Icon.find(cond, one=True)
    if not icon_info:
        raise ValueError("icon:%s not in db", icon_info['title'])
    icon_info["refered_count"] -= 1
    Icon.update(cond, icon_info)
    _LOGGER.info("update the id refer count :%s", icon_id)


def refered_icon(id, old_id=None):
    """
    add the count of referenced icon resource
    """
    Icon = classing_model("icon")
    cond = {}
    icon_id = int(id) if not isinstance(id, int) else id
    cond["id"] = icon_id
    icon_info = Icon.find(cond, one=True)
    if not icon_info:
        raise ValueError("icon:%s not in db", icon_id)
    icon_info["refered_count"] += 1
    Icon.update(cond, icon_info)
    _LOGGER.info("update the id refer count :%s", icon_id)
    if old_id is not None:
        old_cond = {}
        icon_id = int(old_id) if not isinstance(old_id, int) else old_id
        old_cond["id"] = icon_id
        icon_info = Icon.find(old_cond, one=True)
        if not icon_info:
            raise ValueError("icon:%s not in db", icon_id)
        icon_info["refered_count"] -= 1
        Icon.update(old_cond, icon_info)
        _LOGGER.info("update the id refer count :%s", icon_id)


def _icon_query_condition(request, search_fields):
    platform = request.GET.get("platform", "all")
    package = request.GET.get("package", "all")
    icon_type = request.GET.get("type", "all")
    icon_category = request.GET.get("category", "all")
    is_upload_local = request.GET.get("is_upload_local", "all")
    is_upload_ec2 = request.GET.get("is_upload_ec2", "all")
    start_time = request.GET.get("start")
    end_time = request.GET.get("end")
    cond = {}
    for key in search_fields.keys():
        if request.GET.get("searchKeyword"):
            searchKeyword = request.GET.get("searchKeyword")
            cond[key] = {"$regex": searchKeyword}
    if platform != "all":
        cond["platform"] = platform
    if package != "all":
        cond["package"] = int(package)
    if icon_type != "all":
        cond["type"] = icon_type
    if icon_category != "all":
        cond["category"] = icon_category
    if start_time:
        start = time.mktime(time.strptime(start_time, '%Y-%m-%d'))
        end = time.mktime(time.strptime(end_time, '%Y-%m-%d')) + _ONE_DAY
        cond["last_modified"] = {"$gte": start, "$lte": end}
    if is_upload_local == "true":
        cond["is_upload_local"] = True
    elif is_upload_local == "false":
        cond["is_upload_local"] = False
    if is_upload_ec2 == "true":
        cond["is_upload_ec2"] = True
    elif is_upload_ec2 == "false":
        cond["is_upload_ec2"] = False
    return cond
