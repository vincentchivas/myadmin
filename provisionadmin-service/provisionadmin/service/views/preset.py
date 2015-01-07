# -*- coding: utf-8 -*-
import simplejson
import zipfile
import time
import logging
import StringIO
import types
from operator import itemgetter
from django.http import HttpResponse
from provisionadmin.utils.json import json_response_error, json_response_ok
from provisionadmin.decorator import exception_handler
from provisionadmin.utils.validate import MetaValidate
from provisionadmin.utils.validate_params import get_valid_params
from provisionadmin.model.preset import (
    classing_model, get_filters, check_in_ec2, remove_from_ec2,
    ref_get_presetdata, get_lc_pn_by_predataids, get_export_filters,
    save_to_ec2, get_ref_rule_preset)
from provisionadmin.utils.respcode import (
    PARAM_ERROR, METHOD_ERROR, DATA_DELETE_COMFIRM,
    PARAM_REQUIRED, ONLINE_DATA_UNDELETE, DATA_NOT_UPLOAD_TO_PRE,
    DATA_RELETED_BY_OTHER)
from provisionadmin.utils.common import now_timestamp, unixto_string
from provisionadmin.service.views.resource import (
    _update_icon_info, derefered_icon, refered_icon)
from provisionadmin.service.views.gesture import _update_gesture_info


_LOGGER = logging.getLogger("view")
_ONE_DAY = 86400.0
_MAX_VERSION_LIMITED = 4294967295
_ANDROID = "android"
_ADMIN = "admin"
_LOCAL = "local"
_CHINA = "china"
_EC2 = "ec2"
_PRESET_DATA_JSON_DIR = "preset/"
All_FLAG = "all_condition"
DEFAULT_SOURCE = "ofw"
_GENERAL_SEARCH = 101
_CANNOT_DEL_IF_RELET = ["aosruledata", "aosstrategy", "aosgesture"]
_REF_BY_ONE_PRESET = [
    "icon", "aosruledata", "aossharecontent", "aosgesture", "aosstrategy",
    "aosspeeddialdesktop"]
_REF_RULE_MODELS = ["aoslocale", "aospackage", "aosoperator", "aossource"]
_DESKTOP_SHARE_IN_PRESET = ["aosspeeddialdesktop", "aossharecontent"]


def _get_children_model(child_name, parent_model, api_type="add", item_ids=[]):
    '''
     notice: when call add model api, if the model has children models,it
     will return children model data list
    '''
    model_list = []
    Model_Child = classing_model(str(child_name))
    if Model_Child:
        relation = Model_Child.relation
        parents = relation["parent"]
        parent_dict = parents.get(parent_model)
        fields = parent_dict.get("fields")
        display_field = parent_dict.get("display")
        results = Model_Child.find({}, fields, toarray=True)
        for result in results:
            model_dict = {}
            model_id = int(result.get("id"))
            model_dict["value"] = model_id
            model_dict["display"] = result.get(display_field)
            if api_type == "edit" and model_id in item_ids:
                model_dict["selected"] = True
            else:
                model_dict["selected"] = False
            model_list.append(model_dict)
    return model_list


def _check_rule(raw_dict={}, api_type="add", update_id=0):
    passed = False
    msg = ""
    cond = {}
    if api_type == "edit":
        cond["id"] = {"$ne": update_id}
    Rule = classing_model("aosruledata")
    if not Rule.find(cond, toarray=True):
        return True, "First time insert one item"
    min_version = raw_dict.get("min_version")
    max_version = raw_dict.get("max_version")
    if not max_version:
        max_version = _MAX_VERSION_LIMITED
    if min_version > max_version:
        passed = False
        msg = "输入的最大版本号小于最小版本号"
        return passed, msg
    locale_list = raw_dict.get("aoslocale")
    package_list = raw_dict.get("aospackage")
    channel_list = raw_dict.get("aossource")
    if channel_list:
        cond["aossource"] = {"$in": channel_list}
    if locale_list:
        cond["aoslocale"] = {"$in": locale_list}
    cond["aospackage"] = {"$in": package_list}
    rule_list = Rule.find(cond, toarray=True)
    if rule_list:
        check_version = False
        # 当匹配前三个条件仍然能筛选rule,判断version code
        # 当任意version code不满足，flag 为 false
        for rule in rule_list:
            min_ver = rule.get("min_version")
            max_ver = rule.get("max_version")
            if max_version < min_ver or min_version > max_ver:
                check_version = True
            else:
                check_version = False
                msg = "version code 配置有重叠的部分，请仔细检查"
                break
        passed = True if check_version else False
    else:
        passed = True
    return passed, msg


def _get_local_package_preset(rawid):
    result = {}
    predata_ids = []
    locale_name_list = []
    package_name_list = []
    locale_id_list = []
    package_id_list = []
    predata_ids.append(rawid)
    lc_pn = get_lc_pn_by_predataids(predata_ids)
    for lc in lc_pn[0]:
        locale_name_list.append(lc.get("name"))
        locale_id_list.append(lc.get("id"))
    for pn in lc_pn[1]:
        package_name_list.append(pn.get("title"))
        package_id_list.append(pn.get("id"))
    result["aoslocale"] = ",".join(locale_name_list)
    result["aospackage"] = ",".join(package_name_list)
    return result


@exception_handler()
def preset_model_add(req, model_name):
    '''
    notice: when get request, if the model had children model, it will return
    a child model data list
    when post request, it will return add successfully or failed
    Request URL: /admin/P<model_name>/add
    HTTP Method: GET/POST
    when get:
    Parameters: None
    Return:{
        "child_model":[
        {"value":child_id,
          "display_value":child_field
        }
        ]
        }
    when post:
    Parameters: {"field1":value1, "field2":value2,...}
    Return:{
         "status":0,
         "msg":"add successfully"
        }
    '''
    Model_Name = classing_model(str(model_name))
    if Model_Name:
        if req.method == "POST":
            temp_strs = req.raw_post_data
            try:
                temp_dict = simplejson.loads(temp_strs)
            except ValueError as expt:
                _LOGGER.error("model add api para except:%s", expt)
                return json_response_error(
                    PARAM_ERROR,
                    msg="json loads error,check parameters format")
            required_list = Model_Name.required
            for required_para in required_list:
                if temp_dict.get(required_para) is None:
                    return json_response_error(
                        PARAM_REQUIRED,
                        msg="parameter %s request" % required_para)
            for key in temp_dict:
                if key in _REF_BY_ONE_PRESET:
                    origin_dict = temp_dict[key]
                    new_dict = {
                        "id": origin_dict["id"],
                        "title": origin_dict["title"]}
                    temp_dict[key] = new_dict
            check_dict = Model_Name.type_check
            if check_dict:
                for key in check_dict:
                    value = temp_dict.get(key)
                    if value:
                        check_type = check_dict[key].get("type")
                        if not MetaValidate.check_validate(check_type, value):
                            return json_response_error(
                                PARAM_REQUIRED,
                                msg="parameter %s invalid" % key)
                        else:
                            if check_type == "List":
                                data_type = check_dict[key].get("data_type")
                                data_list = temp_dict[key]
                                temp_list = []
                                for item in data_list:
                                    temp_list.append(eval(data_type)(item))
                                temp_dict[key] = temp_list
            if hasattr(Model_Name, "fields_check"):
                fields_convert_dict = Model_Name.fields_check
                temp_dict = get_valid_params(temp_dict, fields_convert_dict)
            if Model_Name.relation and model_name != "aosruledata":
                children = Model_Name.relation.get("children")
                if children:
                    for key in children:
                        children_list = temp_dict.get(key)
                        child_info = children[key]
                        child_fields = child_info.get("fields")
                        if children_list:
                            new_children_list = []
                            for child in children_list:
                                child_dict = {}
                                child_dict["id"] = child.get("id")
                                for field in child_fields:
                                    if field == "order":
                                        try:
                                            value = int(child.get(field))
                                            child_dict[field] = value
                                        except:
                                            raise ValueError
                                    new_children_list.append(child_dict)
                            temp_dict[key] = new_children_list
            if model_name == "aospredata":
                Predata = classing_model("aospredata")
                rule_dict = temp_dict["aosruledata"]
                item = Predata.find(
                    {"aosruledata.id": rule_dict.get("id")}, one=True)
                if item:
                    return json_response_error(
                        PARAM_ERROR,
                        msg="关联的规则已经被其他预置数据引用，请重新选择！")
            if model_name == "aosruledata":
                if not temp_dict.get("aospackage"):
                    return json_response_error(
                        PARAM_ERROR, msg="缺少包名")
                check_results = _check_rule(temp_dict)
                if not check_results[0]:
                    return json_response_error(
                        PARAM_ERROR, msg=check_results[1])
            if temp_dict.get("icon"):
                icon_dict = temp_dict["icon"]
                refered_icon(icon_dict.get("id"))
            result = Model_Name.insert(temp_dict)
            if result == "unique_failed":
                return json_response_error(
                    PARAM_ERROR,
                    msg="unque check failed")
            else:
                temp_dict["id"] = result
            return json_response_ok(
                temp_dict, msg="add %s success" % model_name)
        elif req.method == "GET":
            data = {}
            if hasattr(Model_Name, "resources"):
                for key in Model_Name.resources:
                    res = Model_Name.resources[key]
                    func_name = res.get("func_name")
                    conn_str = res.get("conn_string")
                    _LOGGER.info(func_name)
                    if hasattr(Model_Name, func_name):
                        func = getattr(Model_Name, func_name)
                        if callable(func):
                            data[func_name] = func(conn_str)
                        else:
                            data[func_name] = func
            if Model_Name.relation:
                children = Model_Name.relation.get("children")
                if children:
                    for key in children:
                        model_list = _get_children_model(key, model_name)
                        data[key] = model_list
                    return json_response_ok(data, msg="get %s list" % key)
                else:
                    return json_response_ok({}, msg="no child model")
            else:
                return json_response_ok({}, msg="no relation model")
        else:
            return json_response_error(
                METHOD_ERROR, msg="http method error")
    else:
        return json_response_error(
            PARAM_ERROR, msg="model name %s is not exist" % model_name)


def _search_cond(request, search_fields):
    '''
    notice:when a request comes,combination of the search_fields and the
    request parameter values, return a condition query to mongodb
    '''
    cond = {}
    for key in search_fields.keys():
        value = request.GET.get(key)
        if value:
            value_dict = search_fields.get(key)
            value_type = value_dict.get("type")
            if value_type == "list":
                value_data_type = value_dict.get("data_type")
                if value_data_type:
                    if value_data_type == "int":
                        cond[key] = int(value)
                    else:
                        cond[key] = value
        else:
            if search_fields.get(key)["type"] == "date":
                start_time = request.GET.get("start")
                if not start_time:
                    continue
                start = time.mktime(
                    time.strptime(start_time, '%Y-%m-%d'))
                end_time = request.GET.get("end")
                end = time.mktime(
                    time.strptime(end_time, '%Y-%m-%d')) + _ONE_DAY
                cond[key] = {"$gte": start, "$lte": end}
            # 当给searchKeyword时候，能全局搜索
            if search_fields.get(key)["type"] == "text":
                if request.GET.get("searchKeyword"):
                    searchKeyword = request.GET.get("searchKeyword")
                    cond[key] = {"$regex": searchKeyword}
    return cond


@exception_handler()
def preset_model_list(req, model_name):
    '''
    Request URL: /admin/preset_{P<model>}_list
    HTTP Method: GET
    Parameters: None
    Return:
        {
            "status":0,
            "data":{
                "items":[
                {"field1":value1},
                {"field2":value2}
                ],
                "total":123
                }
            }

    '''
    Model_Name = classing_model(str(model_name))
    if Model_Name:
        if req.method == "GET":
            model_list = []
            cond = {}
            list_api = {}
            if hasattr(Model_Name, "list_api"):
                list_api = Model_Name.list_api
            else:
                return json_response_error(
                    PARAM_ERROR, msg="list_api is not configed")
            fields = list_api["fields"]
            query_dict = req.GET
            pageindex = query_dict.get("index")
            pagesize = query_dict.get("limit")
            if not pageindex:
                pageindex = 1
            if not pagesize:
                pagesize = 20
            if list_api.get("search_fields"):
                search_fields = list_api["search_fields"]
                cond = _search_cond(req, search_fields)
            results = Model_Name.find(
                cond, fields=fields).sort(
                'last_modified', -1).skip(
                (int(pageindex) - 1) * int(pagesize)).limit(int(pagesize))
            total = Model_Name.find(cond).count()
            for result in results:
                result.pop("_id", None)
                if hasattr(Model_Name, "ref_preset_data"):
                    ref_dict = Model_Name.ref_preset_data
                    predata_ids = []
                    model_id = result.get("id")
                    if model_name in _REF_RULE_MODELS:
                        predata_ids = get_ref_rule_preset(
                            model_name, model_id)
                        Model_Name.update(
                            {"id": result.get("id")},
                            {"ref_preset_id": predata_ids})
                    else:
                        for key in ref_dict:
                            object_link = ref_dict[key]
                            predata_ids = predata_ids + ref_get_presetdata(
                                model_id, model_name, object_link)
                        if predata_ids:
                            lc_pn = get_lc_pn_by_predataids(
                                list(set(predata_ids)))
                            locale_name_list = []
                            locale_id_list = []
                            package_name_list = []
                            package_id_list = []
                            for lc in lc_pn[0]:
                                locale_name_list.append(lc.get("name"))
                                locale_id_list.append(lc.get("id"))
                            for pn in lc_pn[1]:
                                package_name_list.append(pn.get("title"))
                                package_id_list.append(pn.get("id"))
                            result["aoslocale"] = ",".join(
                                list(set(locale_name_list)))
                            result["aospackage"] = ",".join(
                                list(set(package_name_list)))
                            Model_Name.update(
                                {"id": result.get("id")},
                                {"aoslocale": list(set(locale_id_list)),
                                    "aospackage": list(set(package_id_list)),
                                    "ref_preset_id": list(set(predata_ids))})
                        else:
                            Model_Name.update(
                                {"id": result.get("id")},
                                {"ref_preset_id": []})
                if model_name == "aospredata":
                    predata_ids = []
                    locale_name_list = []
                    package_name_list = []
                    locale_id_list = []
                    package_id_list = []
                    predata_ids.append(result.get("id"))
                    lc_pn = get_lc_pn_by_predataids(predata_ids)
                    for lc in lc_pn[0]:
                        locale_name_list.append(lc.get("name"))
                        locale_id_list.append(lc.get("id"))
                    for pn in lc_pn[1]:
                        package_name_list.append(pn.get("title"))
                        package_id_list.append(pn.get("id"))
                    result["aoslocale"] = ",".join(locale_name_list)
                    result["aospackage"] = ",".join(package_name_list)
                    last_modified = result.get("last_modified")
                    if result.get("last_modified"):
                        release_local_time = result.get("last_release_local")
                        release_ec2_time = result.get("last_release_ec2")
                        if last_modified > release_local_time:
                            # need upload
                            if release_local_time > release_ec2_time:
                                result["release"] = 2
                            else:
                                result["release"] = 1
                        else:
                            if release_local_time > release_ec2_time:
                                result["release"] = 2
                            else:
                                result["release"] = 0
                    Model_Name.update(
                        {"id": result.get("id")},
                        {"aoslocale": list(set(locale_id_list)),
                            "aospackage": list(set(package_id_list)),
                            "release": result["release"]})
                result["last_modified"] = unixto_string(
                    result.get("last_modified"))
                if result.get("first_created"):
                    result["first_created"] = unixto_string(
                        result.get("first_created"))
                model_list.append(result)
            data = {}
            data["total"] = total
            if list_api.get("get_filters"):
                params = list_api.get("get_filters")
                filters = get_filters(params)
                data["filters"] = filters
            data["items"] = model_list
            return json_response_ok(data, msg="get list")
        else:
            return json_response_error(
                METHOD_ERROR, msg="http method error")
    else:
        return json_response_error(
            PARAM_ERROR, msg="model name %s is not exist" % model_name)


@exception_handler()
def preset_model_detail(req, model_name):
    '''
     notice:get one  item detail
     url: /admin/model_name/edit?id=xxxxxxxxxxxxxxx
     http method: get
        return:{
            "item":{
                "field1":value1,
                "field2":value2
                }
            }
    '''
    Model_Name = classing_model(str(model_name))
    if Model_Name:
        if req.method == "GET":
            item_id = req.GET.get("id")
            if not item_id:
                return json_response_error(
                    PARAM_ERROR, msg="the id is required")
            cond = {"id": int(item_id)}
            detail_item = Model_Name.find(cond, one=True, toarray=True)
            if detail_item:
                data = {}
                detail_item.pop("_id", None)
                if Model_Name.relation and model_name != "aosruledata":
                    children = Model_Name.relation.get("children")
                    if children:
                        for key in children:
                            Child_Model = classing_model(str(key))
                            new_children_list = []
                            child_info_list = detail_item[key]
                            for child_info in child_info_list:
                                child_id = child_info["id"]
                                child_detail = Child_Model.find(
                                    {"id": child_id}, one=True)
                                if child_detail:
                                    child_detail.pop("_id", None)
                                    if child_detail:
                                        for child_item in child_info:
                                            child_detail[
                                                child_item] = child_info[
                                                child_item]
                                        new_children_list.append(child_detail)
                            detail_item[key] = new_children_list
                data["item"] = detail_item
                if model_name == "aosruledata":
                    if Model_Name.relation:
                        children = Model_Name.relation.get("children")
                        if children:
                            for key in children:
                                item_ids = detail_item.get(key)
                                model_list = _get_children_model(
                                    key, model_name,
                                    api_type="edit", item_ids=item_ids)
                                detail_item[key] = model_list
                            return json_response_ok(
                                detail_item,
                                msg="edit api:children model %s list" % key)
                        else:
                            return json_response_ok(
                                detail_item, msg="no child model")
                    else:
                        return json_response_ok(
                            detail_item, msg="no relation model")
                else:
                    return json_response_ok(
                        detail_item, msg="general detail item return")
            else:
                return json_response_error(
                    PARAM_ERROR, msg="the id is not exist")
        else:
            return json_response_error(
                METHOD_ERROR, msg="http method error")
    else:
        return json_response_error(
            PARAM_ERROR, msg="model name %s is not exist" % model_name)


@exception_handler()
def preset_model_modify(req, model_name):
    '''
     notice:update one item of a model
     url :  /admin/model_name/update
     parameter:{"field1":value1, "field2:value2"}
     return:{
        "status":0,
        "msg":"save successfully"
        }
    '''
    Model_Name = classing_model(str(model_name))
    if Model_Name:
        if req.method == "POST":
            required_list = Model_Name.required
            temp_strs = req.raw_post_data
            try:
                temp_dict = simplejson.loads(temp_strs)
            except ValueError as expt:
                _LOGGER.error("model edit api params except:%s", expt)
                return json_response_error(
                    PARAM_ERROR,
                    msg="json loads error,check parameters format")
            item_id = temp_dict.get("id")
            for required_para in required_list:
                para_value = temp_dict.get(required_para)
                if para_value == "" or para_value == [] or para_value == {}:
                    return json_response_error(
                        PARAM_REQUIRED,
                        msg="parameter %s request" % required_para)
            for key in temp_dict:
                if key in _REF_BY_ONE_PRESET:
                    origin_dict = temp_dict[key]
                    if origin_dict:
                        new_dict = {
                            "id": origin_dict["id"],
                            "title": origin_dict["title"]}
                        temp_dict[key] = new_dict
            check_dict = Model_Name.type_check
            if check_dict:
                for key in check_dict:
                    value = temp_dict.get(key)
                    if value:
                        check_type = check_dict[key].get("type")
                        if not MetaValidate.check_validate(check_type, value):
                            return json_response_error(
                                PARAM_REQUIRED,
                                msg="parameter %s invalid" % key)
                        else:
                            if check_type == "List":
                                data_type = check_dict[key].get("data_type")
                                data_list = temp_dict[key]
                                temp_list = []
                                for item in data_list:
                                    temp_list.append(eval(data_type)(item))
                                temp_dict[key] = temp_list
            cond = {"id": int(item_id)}
            if hasattr(Model_Name, "fields_check"):
                fields_convert_dict = Model_Name.fields_check
                temp_dict = get_valid_params(temp_dict, fields_convert_dict)
            if model_name == "aospredata":
                Predata = classing_model("aospredata")
                old_predata = Predata.find(cond, one=True)
                old_rule = old_predata.get("aosruledata")
                rule_dict = temp_dict["aosruledata"]
                temp_dict["last_modified"] = now_timestamp()
                temp_dict["release"] = 1
                if rule_dict.get("id") != old_rule.get("id"):
                    check_unique_cond = {}
                    check_unique_cond["aosruledata.id"] = int(
                        rule_dict.get("id"))
                    item = Predata.find(check_unique_cond, toarray=True)
                    if len(item) >= 1:
                        ref_item = item[0]
                        item_id = ref_item["id"]
                        return json_response_error(
                            PARAM_ERROR,
                            msg="关联的规则已经被preset_id:%d 引用" % item_id)
            if model_name == "aosruledata":
                if not temp_dict.get("aospackage"):
                    return json_response_error(
                        PARAM_ERROR, msg="缺少包名")
                para_list = ("aoslocale", "aossource", "aosoperator")
                for para in para_list:
                    if not temp_dict.get(para):
                        temp_dict[para] = [0]
                check_results = _check_rule(
                    temp_dict, api_type="edit", update_id=int(item_id))
                if not check_results[0]:
                    return json_response_error(
                        PARAM_ERROR, msg=check_results[1])
            check_unique_cond = Model_Name.build_unique_cond(temp_dict)
            check_unique_cond["id"] = {"$ne": int(item_id)}
            another_item = Model_Name.find(
                check_unique_cond, one=True, toarray=True)
            if another_item:
                return json_response_error(
                    PARAM_ERROR, msg="update error, check unique error")
            item_old = Model_Name.find(cond, one=True)
            if item_old:
                temp_dict.pop("_id", None)
                temp_dict.pop("id", None)
                temp_dict["last_modified"] = now_timestamp()
                if Model_Name.relation and model_name != "aosruledata":
                    children = Model_Name.relation.get("children")
                    if children:
                        for key in children:
                            children_list = temp_dict.get(key)
                            child_info = children[key]
                            child_fields = child_info.get("fields")
                            if children_list:
                                new_children_list = []
                                for child in children_list:
                                    child_dict = {}
                                    child_dict["id"] = child.get("id")
                                    for field in child_fields:
                                        if field == "order":
                                            try:
                                                value = int(child.get(field))
                                                child_dict[field] = value
                                            except:
                                                raise ValueError
                                        new_children_list.append(child_dict)
                                temp_dict[key] = new_children_list
                if temp_dict.get("icon"):
                    icon_dict = temp_dict["icon"]
                    old_icon_dict = item_old["icon"]
                    new_icon_id = icon_dict.get("id")
                    old_icon_id = old_icon_dict.get("id")
                    refered_icon(new_icon_id, old_icon_id)
                Model_Name.update(cond, temp_dict)
                _LOGGER.info("the id:%s is saved successful", item_id)
                return json_response_ok(
                    temp_dict, msg="update %s success" % model_name)
            else:
                _LOGGER.info("the id:%s is not exist", item_id)
                return json_response_error(
                    PARAM_ERROR, msg="the  id: %s is not exist" % item_id)
        else:
            return json_response_error(
                METHOD_ERROR, msg="http method error")
    else:
        return json_response_error(
            PARAM_ERROR, msg="model name %s is not exist" % model_name)


def _del_model_with_relations(model_name, item_id, comfirm=False):
    Model_Name = classing_model(str(model_name))
    relation = Model_Name.relation
    parent_dict = {}
    if relation.get("parent"):
        parent_dict = relation.get("parent")
    item_id = int(item_id)
    model = Model_Name.find(cond={"id": item_id}, one=True)
    if model:
        if parent_dict:
            for key in parent_dict:
                fields_in_parent = model_name
                if key == "aosruledata":
                    # 子model在父model中的字段名字，rule model存储为数组id
                    Rule = classing_model("aosruledata")
                    model_list = Rule.find(
                        {fields_in_parent: item_id}, toarray=True)
                    if model_list:
                        if comfirm:
                            for mod in model_list:
                                child_list = mod.get(fields_in_parent)
                                child_list.remove(item_id)
                                Rule.update(
                                    {"id": mod["id"]},
                                    {fields_in_parent: child_list})
                        else:
                            return DATA_DELETE_COMFIRM
                    else:
                        _LOGGER.info("rule data model has no ref id")
                elif model_name not in _DESKTOP_SHARE_IN_PRESET:
                    # 一般的父model存储子model：[{"id":1},{"id":2}]
                    Parent_Model = classing_model(str(key))
                    id_fields_in_parent = model_name + ".id"
                    model_list = Parent_Model.find(
                        {id_fields_in_parent: item_id}, toarray=True)
                    if model_list:
                        for mod in model_list:
                            child_list = mod.get(fields_in_parent)
                            for id_dict in child_list:
                                if id_dict.get("id") == item_id:
                                    if comfirm:
                                        child_list.remove(id_dict)
                                    else:
                                        return DATA_DELETE_COMFIRM
                            Parent_Model.update(
                                {"id": mod["id"]},
                                {fields_in_parent: child_list})
                    else:
                        _LOGGER.info("parent model has no ref id")
                else:
                    # 特殊的父model存储子model：{"id":1}
                    Parent_Model = classing_model(str(key))
                    id_fields_in_parent = model_name + ".id"
                    model_list = Parent_Model.find(
                        {id_fields_in_parent: item_id}, toarray=True)
                    if model_list:
                        for mod in model_list:
                            child_dict = mod.get(fields_in_parent)
                            if child_dict:
                                if comfirm:
                                    child_dict = {}
                                else:
                                    return DATA_DELETE_COMFIRM
                            Parent_Model.update(
                                {"id": mod["id"]},
                                {fields_in_parent: child_dict})
                    else:
                        _LOGGER.info("parent model has no ref id")
        else:
            _LOGGER.info("%s has no parent model" % model_name)
        if model.get("icon"):
            icon_dict = model.get("icon")
            old_icon_id = icon_dict.get("id")
            derefered_icon(old_icon_id)
        Model_Name.remove({"id": item_id})
    else:
        _LOGGER.info(
            "model %s itemid %s is not exist" % (model_name, item_id))


def _del_predata(place, rawids):
    status = 0
    delete_success = []
    delete_failed = []
    Predata = classing_model("aospredata")
    Preset_Local = classing_model("preset_local")
    count = len(rawids)
    if place == _ADMIN:
        for rawid in rawids:
            item = Preset_Local.find({"id": rawid}, one=True)
            raw_item = Predata.find({"id": rawid}, one=True)
            raw_item.pop("_id", None)
            raw_item["last_modified"] = unixto_string(
                raw_item["last_modified"])
            raw_item["first_created"] = unixto_string(
                raw_item["first_created"])
            lc_pn = _get_local_package_preset(rawid)
            raw_item["aoslocale"] = lc_pn.get("aoslocale")
            raw_item["aospackage"] = lc_pn.get("aospackage")
            if not item:
                count = count - 1
                Predata.remove({"id": rawid})
                delete_success.append(raw_item)
                _LOGGER.info(
                    "id:%d delete from admin success", rawid)
            else:
                status = ONLINE_DATA_UNDELETE
                delete_failed.append(raw_item)
                _LOGGER.error("id:%d should delete from local first" % rawid)
    elif place == _LOCAL:
        for rawid in rawids:
            if not check_in_ec2(rawid):
                count = count - 1
                Preset_Local.remove({"id": rawid})
                Predata.update(
                    {"id": rawid},
                    {"is_upload_local": False, "release": 1})
                raw_item = Predata.find({"id": rawid}, one=True)
                raw_item.pop("_id", None)
                raw_item["last_modified"] = unixto_string(
                    raw_item["last_modified"])
                raw_item["first_created"] = unixto_string(
                    raw_item["first_created"])
                lc_pn = _get_local_package_preset(rawid)
                raw_item["aoslocale"] = lc_pn.get("aoslocale")
                raw_item["aospackage"] = lc_pn.get("aospackage")
                delete_success.append(raw_item)
                _LOGGER.info(
                    "id:%d delete from local success", rawid)
            else:
                status = ONLINE_DATA_UNDELETE,
                raw_item = Predata.find({"id": rawid}, one=True)
                raw_item.pop("_id", None)
                raw_item["last_modified"] = unixto_string(
                    raw_item["last_modified"])
                raw_item["first_created"] = unixto_string(
                    raw_item["first_created"])
                lc_pn = _get_local_package_preset(rawid)
                raw_item["aoslocale"] = lc_pn.get("aoslocale")
                raw_item["aospackage"] = lc_pn.get("aospackage")
                delete_failed.append(raw_item)
                _LOGGER.error("id:%d should delete from ec2 first" % rawid)
    elif place == _EC2:
        for rawid in rawids:
            raw_item = Predata.find({"id": rawid}, one=True)
            count = count - 1
            remove_from_ec2(rawid)
            Predata.update(
                {"id": rawid},
                {"is_upload_ec2": False, "release": 2})
            raw_item = Predata.find({"id": rawid}, one=True)
            raw_item.pop("_id", None)
            raw_item["last_modified"] = unixto_string(
                raw_item["last_modified"])
            raw_item["first_created"] = unixto_string(
                raw_item["first_created"])
            lc_pn = _get_local_package_preset(rawid)
            raw_item["aoslocale"] = lc_pn.get("aoslocale")
            raw_item["aospackage"] = lc_pn.get("aospackage")
            delete_success.append(raw_item)
            _LOGGER.info(
                "id:%d delete from ec2 success", rawid)
    else:
        status = -1
    return status, delete_success, delete_failed


@exception_handler()
def preset_model_delete(req, model_name):
    '''
    Request URL: /admin/P<model_name>/delete
    HTTP Method: POST
    Parameters: {"item_ids": ["123","124"]}
    Return:{
        "status":0,
        "msg":"delete successfully"
        }
    '''
    Model_Name = classing_model(str(model_name))
    item_ids = []
    temp_dict = {}
    if Model_Name:
        if req.method == "POST":
            temp_strs = req.raw_post_data
            try:
                temp_dict = simplejson.loads(temp_strs)
            except ValueError as expt:
                _LOGGER.info("model delete api para except:%s", expt)
                return json_response_error(
                    PARAM_ERROR,
                    msg="json loads error,check parameters format")
            if model_name == "aospredata":
                items = temp_dict.get("items")
                place = temp_dict.get("server")
                for item in items:
                    item_ids.append(int(item))
                results = _del_predata(place, item_ids)
                status = results[0]
                data = {}
                data["delete_success"] = results[1]
                data["delete_failed"] = results[2]
                if status == -1:
                    return json_response_error(
                        PARAM_ERROR, msg="UNKNOWN UPLOAD PLACE")
                elif status == 0:
                    if place == _ADMIN:
                        suc_ids = []
                        fail_ids = []
                        if data["delete_failed"]:
                            for fai_item in data["delete_failed"]:
                                fail_ids.append(fai_item.get("id"))
                        if data["delete_success"]:
                            for suc_item in data["delete_success"]:
                                suc_ids.append(suc_item.get("id"))
                        data["delete_success"] = suc_ids
                        data["delete_failed"] = fail_ids
                    return json_response_ok(
                        data, msg="delete successfully")
                else:
                    return json_response_error(status, msg="delete error")
            else:
                item_ids = temp_dict.get("items")
            if not item_ids:
                return json_response_error(PARAM_ERROR, msg="item_id is empty")
            else:
                comfirm = temp_dict.get("comfirm")
                if comfirm is None:
                    comfirm = False
                else:
                    comfirm = True
                delete_ids = []
                for item in item_ids:
                    if not comfirm:
                        if hasattr(Model_Name, "ref_preset_data"):
                            result = Model_Name.find(
                                {"id": int(item)}, one=True)
                            ref_preset_ids = result.get("ref_preset_id")
                            if ref_preset_ids:
                                list_all = _CANNOT_DEL_IF_RELET +\
                                    _REF_RULE_MODELS
                                if model_name in list_all:
                                    return json_response_error(
                                        DATA_RELETED_BY_OTHER,
                                        msg="id:%d refence by preset_id: %s" %
                                        (int(item), ref_preset_ids[0]))
                                else:
                                    return json_response_error(
                                        DATA_DELETE_COMFIRM,
                                        msg="id:%d refence by preset_id: %s" %
                                        (int(item), ref_preset_ids[0]))
                            else:
                                if model_name in _REF_RULE_MODELS:
                                    ret_val = _del_model_with_relations(
                                        str(model_name), item, comfirm)
                                    if ret_val:
                                        return json_response_error(
                                            DATA_RELETED_BY_OTHER,
                                            msg="id refered by rule")
                                    else:
                                        _del_model_with_relations(
                                            str(model_name), item, True)
                                        delete_ids.append(item)
                                else:
                                    ret_val = _del_model_with_relations(
                                        str(model_name), item, comfirm)
                                    if ret_val:
                                        return json_response_error(
                                            DATA_DELETE_COMFIRM,
                                            msg="item has been refered")
                                    delete_ids.append(item)
                        else:
                            _del_model_with_relations(
                                str(model_name), item)
                            delete_ids.append(item)
                    else:
                        _del_model_with_relations(
                            str(model_name), item, comfirm)
                        delete_ids.append(item)
                return json_response_ok(delete_ids, msg="delete success")

        else:
            return json_response_error(
                METHOD_ERROR, msg="http method error")
    else:
        return json_response_error(
            PARAM_ERROR, msg="model name %s is not exist" % model_name)


def _get_icon_url(icon_dict={}, server_name=_LOCAL):
    if not icon_dict:
        return ""
    else:
        icon_id = icon_dict.get("id")
        icon_list = []
        icon_list.append(icon_id)
        icon_info = _update_icon_info(icon_list, server_name)[0]
        if icon_info:
            icon = icon_info[0]
            url_name = "%s_url" % server_name
            return icon.get(url_name)
        else:
            return ""


def _get_gesture_url(gesture_dict={}, server_name=_LOCAL):
    if not gesture_dict:
        return ""
    else:
        gesture_id = gesture_dict.get("id")
        gesture_list = []
        gesture_list.append(gesture_id)
        gesture_info_list = _update_gesture_info(gesture_list, server_name)[0]
        server_url = "%s_url" % server_name
        if gesture_info_list:
            gesture_info = gesture_info_list[0]
            return gesture_info.get(server_url)
        else:
            return ""


def _package_share(shareid, server_name):
    share_dict = {}
    share_content_dict = {}
    ShareContent = classing_model("aossharecontent")
    Template = classing_model("aostemplateshare")
    Recommend = classing_model("aosrecommendshare")
    sharecontent = ShareContent.find(
        {"id": shareid}, one=True, toarray=True)
    if not sharecontent:
        return {}
    share_content_dict["app_url"] = sharecontent.get("app_url")
    share_content_dict["webpage_template"] = sharecontent.get(
        "webpage_template")
    homepage_template = []
    templateshare_list = sharecontent.get("aostemplateshare")
    if templateshare_list:
        for template in templateshare_list:
            template_id = template.get("id")
            temp = Template.find(
                {"id": int(template_id)}, one=True, toarray=True)
            homepage_template.append(temp.get("template_text"))
    share_content_dict["homepage_template"] = homepage_template
    share_dict["share_content"] = share_content_dict
    recommend_shares = []
    recommend_shares_ids = sharecontent.get("aosrecommendshare")
    if recommend_shares_ids:
        for id_dict in recommend_shares_ids:
            temp_dict = {}
            recommend_id = id_dict.get("id")
            temp = Recommend.find(
                {"id": int(recommend_id)}, one=True, toarray=True)
            temp_dict["unique_name"] = temp.get("title")
            temp_dict["icon"] = _get_icon_url(temp.get("icon"), server_name)
            temp_dict["share_url"] = temp.get("url")
            temp_dict["package_name"] = temp.get("packagename")
            temp_dict["title"] = temp.get("name")
            recommend_shares.append(temp_dict)
    share_dict["recommend_shares"] = recommend_shares
    return share_dict


def _package_speeddials(desktopid, server_name):
    Destop = classing_model("aosspeeddialdesktop")
    Screen = classing_model("aosspeeddialscreen")
    Folder = classing_model("aosspeeddialfolder")
    Item = classing_model("aosspeeddial")
    screen_list = []
    des = Destop.find({"id": int(desktopid)}, one=True)
    screen_ids = des.get("aosspeeddialscreen")
    if screen_ids:
        for screen_id in screen_ids:
            screen_dict = {}
            screen_dict["id"] = screen_id.get("id")
            screen_capture = []
            screen = Screen.find(
                {"id": int(screen_id.get("id"))}, one=True, toarray=True)
            screen_dict["sid"] = int(screen.get("sid"))
            fold_ids = screen.get("aosspeeddialfolder")
            item_ids = screen.get("aosspeeddial")
            for item_id in item_ids:
                item_dict = {}
                item = Item.find(
                    {"id": int(item_id.get("id"))},
                    one=True, toarray=True)
                item_dict["url"] = item.get("url")
                item_dict["ico"] = _get_icon_url(item.get("icon"), server_name)
                item_dict["ttl"] = item.get("name")
                item_dict["d"] = item.get("allowdel")
                if item_id.get("order") is None:
                    item_dict["p"] = 0
                else:
                    item_dict["p"] = int(item_id.get("order"))
                screen_capture.append(item_dict)
            for fold_id in fold_ids:
                fold_dict = {}
                if fold_id.get("order") is None:
                    fold_dict["p"] = 0
                else:
                    fold_dict["p"] = int(fold_id.get("order"))
                folder = Folder.find(
                    {"id": int(fold_id.get("id"))},
                    one=True, toarray=True)
                item_ids_infolder = folder.get("aosspeeddial")
                item_list = []
                for item_id in item_ids_infolder:
                    item_dict = {}
                    item = Item.find(
                        {"id": int(item_id.get("id"))},
                        one=True, toarray=True)
                    item_dict["url"] = item.get("url")
                    item_dict["ico"] = _get_icon_url(
                        item.get("icon"), server_name)
                    item_dict["ttl"] = item.get("name")
                    item_dict["d"] = item.get("allowdel")
                    if item_id.get("order"):
                        item_dict["p"] = int(item_id.get("order"))
                    else:
                        item_dict["p"] = 0
                    item_list.append(item_dict)
                fold_dict["its"] = sorted(item_list, key=itemgetter("p"))
                fold_dict["ttl"] = folder.get("name")
                if fold_id.get("order") is None:
                    fold_dict["p"] = 0
                else:
                    fold_dict["p"] = int(fold_id.get("order"))
                screen_capture.append(fold_dict)
            screen_dict["its"] = sorted(screen_capture, key=itemgetter("p"))
            screen_list.append(screen_dict)
    return screen_list


def _package_bookmarks(bookmarks, bookmark_folders):
    Bookmark = classing_model("aosbookmark")
    Bookmarkfolder = classing_model("aosbookmarkfolder")
    bookmark_list = []
    if bookmarks:
        for bookmark_id in bookmarks:
            bookmark_dict = {}
            bookmark = Bookmark.find(
                {"id": int(bookmark_id.get("id"))}, one=True, toarray=True)
            bookmark_dict["name"] = bookmark.get("name")
            bookmark_dict["url"] = bookmark.get("url")
            if bookmark_id.get("order") is None:
                bookmark_dict["order"] = 0
            else:
                bookmark_dict["order"] = int(bookmark_id.get("order"))
            bookmark_list.append(bookmark_dict)
    if bookmark_folders:
        for bookmarkfolder_id in bookmark_folders:
            bookmarkfolder = Bookmarkfolder.find(
                {"id": int(bookmarkfolder_id.get("id"))},
                one=True, toarray=True)
            fold_dict = {}
            item_list = []
            item_ids = bookmarkfolder.get("aosbookmark")
            for item_id in item_ids:
                bookmark_dict = {}
                bookmark = Bookmark.find(
                    {"id": int(item_id.get("id"))}, one=True, toarray=True)
                bookmark_dict["name"] = bookmark.get("name")
                bookmark_dict["url"] = bookmark.get("url")
                if item_id.get("order") is None:
                    bookmark_dict["order"] = 0
                else:
                    bookmark_dict["order"] = int(item_id.get("order"))
                item_list.append(bookmark_dict)
            fold_dict["bookmarks"] = sorted(item_list, key=itemgetter("order"))
            fold_dict["name"] = bookmarkfolder.get("name")
            if bookmarkfolder_id.get("order") is None:
                fold_dict["order"] = 0
            else:
                fold_dict["order"] = int(bookmarkfolder_id.get("order"))
            bookmark_list.append(fold_dict)
    return sorted(bookmark_list, key=itemgetter("order"))


def _package_searchers(searcher_folders, server_name=_LOCAL):
    Searcher = classing_model("aossearcher")
    Searcherfolder = classing_model("aossearcherfolder")
    search_engines = []
    for folder_id in searcher_folders:
        folder_dict = {}
        search_list = []
        folder = Searcherfolder.find(
            {"id": int(folder_id.get("id"))}, one=True, toarray=True)
        defalut_id = folder.get("defaultCheck")
        item_ids = folder.get("aossearcher")
        default_count = 0
        for item_id in item_ids:
            item_dict = {}
            item = Searcher.find(
                {"id": int(item_id.get("id"))}, one=True, toarray=True)
            extend_dict = item.get("extend")
            if item_id.get("id") == defalut_id:
                item_dict["default"] = True
            else:
                item_dict["default"] = False
                default_count = default_count + 1
            item_dict["id"] = item.get("id")
            item_dict["suggest"] = item.get("suggest")
            item_dict["url"] = item.get("url")
            item_dict["icon"] = _get_icon_url(item.get("icon"), server_name)
            if extend_dict:
                try:
                    extend_dict = simplejson.loads(extend_dict)
                except:
                    raise ValueError
            if isinstance(extend_dict, types.DictType):
                for key in extend_dict:
                    item_dict[key] = extend_dict[key]
            item_dict["title"] = item.get("name")
            if item_id.get("order") is None:
                item_dict["order"] = 0
            else:
                item_dict["order"] = int(item_id.get("order"))
            search_list.append(item_dict)
        if default_count == len(item_ids):
            _LOGGER.error("no default searcher")
        folder_dict["title"] = folder.get("name")
        folder_dict["layout"] = _GENERAL_SEARCH
        folder_dict["searches"] = sorted(search_list, key=itemgetter("order"))
        search_engines.append(folder_dict)
    return search_engines


def _package_ruledata(ruleid):
    Ruledata = classing_model("aosruledata")
    Source = classing_model("aossource")
    Locale = classing_model("aoslocale")
    Operator = classing_model("aosoperator")
    Package = classing_model("aospackage")
    rule = Ruledata.find({"id": ruleid}, one=True, toarray=True)
    locale_ids = rule.get("aoslocale")
    operator_ids = rule.get("aosoperator")
    package_ids = rule.get("aospackage")
    source_ids = rule.get("aossource")
    locale_list = []
    if locale_ids == [] or locale_ids == [0]:
        locale_list.append(All_FLAG)
    else:
        for locale_id in locale_ids:
            locale = Locale.find(
                {"id": locale_id}, one=True, toarray=True)
            locale_list.append(locale.get("name"))
    operator_list = []
    if operator_ids == [] or operator_ids == [0]:
        operator_list.append(All_FLAG)
    else:
        for operator_id in operator_ids:
            operator = Operator.find(
                {"id": operator_id}, one=True, toarray=True)
            operator_list.append(operator.get("code"))
    packagename_list = []
    if package_ids:
        for package_id in package_ids:
            package = Package.find(
                {"id": package_id}, one=True, toarray=True)
            packagename_list.append(package.get("package_name"))
    source_list = []
    if source_ids == [] or source_ids == [0]:
        source_list.append(All_FLAG)
    else:
        for source_id in source_ids:
            source = Source.find(
                {"id": source_id}, one=True, toarray=True)
            source_list.append(source.get("title"))
    rule_dict = {}
    rule_dict["min_version"] = rule.get("min_version")
    rule_dict["max_version"] = rule.get("max_version")
    rule_dict["locales"] = locale_list
    rule_dict["sources"] = source_list
    rule_dict["packages"] = packagename_list
    rule_dict["operators"] = operator_list
    rule_dict["os"] = _ANDROID
    return rule_dict


def _package_one_predata(rawid, server_name=_LOCAL):
    pre_dict = {}
    check_success = True
    msg = ""
    # init classes
    Predata = classing_model("aospredata")
    Gesture = classing_model("aosgesture")
    Strategy = classing_model("aosstrategy")
    predata = Predata.find(cond={"id": rawid}, one=True, toarray=True)
    predata_dict = {}
    # package share
    share_dict = {}
    share_content_id = predata.get("aossharecontent")
    if share_content_id:
        share_dict = _package_share(
            int(share_content_id.get("id")), server_name)
    predata_dict["shares"] = share_dict
    # print share_dict
    # package speeddials
    speeddial_destop = predata.get("aosspeeddialdesktop")
    speeddial_list = []
    if speeddial_destop:
        speeddial_list = _package_speeddials(
            speeddial_destop.get("id"), server_name)
    predata_dict["speeddials"] = speeddial_list
    # print speeddial_list
    # package bookmark
    bookmarks = predata.get("aosbookmark")
    bookmark_folders = predata.get("aosbookmarkfolder")
    bookmark_list = []
    if bookmarks or bookmark_folders:
        bookmark_list = _package_bookmarks(bookmarks, bookmark_folders)
    predata_dict["bookmarks"] = bookmark_list
    # search engine
    searcher_folders = predata.get("aossearcherfolder")
    search_engines = []
    if searcher_folders:
        search_engines = _package_searchers(searcher_folders, server_name)
        if search_engines is None:
            check_success = False
            msg = 'no default search engine'
    predata_dict["search_engines"] = search_engines
    # print search_engines
    # Strategy
    strategy = predata.get("aosstrategy")
    strategy_dict = {}
    if strategy:
        strategy = Strategy.find(
            {"id": int(strategy.get("id"))}, one=True)
        strategy_dict["duration"] = strategy.get("duration")
        strategy_dict["tutorials"] = strategy.get("tutorials").split(',')
        strategy_dict["strategy_test"] = False
        strategy_dict["id"] = strategy.get("id")
    predata_dict["strategy"] = strategy_dict
    # gesture
    gesture = predata.get("aosgesture")
    gesture_dict = {}
    if gesture:
        gesture_item = Gesture.find(
            {"id": int(gesture.get("id"))}, one=True)
        gesture_dict["marked_file"] = gesture_item.get("marked_file")
        try:
            gesture_dict["user_gesture_file"] = _get_gesture_url(
                gesture_item, server_name)
        except:
            check_success = False
            msg = 'package gesture file error'
    predata_dict["gesture"] = gesture_dict
    #  rule configure
    rule_id = predata.get("aosruledata")
    rule_dict = {}
    if rule_id:
        rule_dict = _package_ruledata(int(rule_id.get("id")))
        if rule_dict.get("packages"):
            pre_dict["_rule"] = rule_dict
        else:
            pre_dict["_rule"] = {}
            check_success = False
            msg = "package is empty"
    else:
        check_success = False
    # package other fields
    field_list = [
        "more_addon_link", "about",
        "home_page", "rate_me_link", "more_theme_link",
        "hotapps", "check_update_link", "tutorial"]
    for field in field_list:
        predata_dict[field] = predata.get(field)
    predata_dict["show_download_translate"] = True
    predata_dict["data_test"] = False
    predata_dict["id"] = predata.get("id")
    # package predata
    pre_dict["_meta"] = predata_dict
    pre_dict["first_created"] = predata.get("first_created")
    pre_dict["last_modified"] = predata.get("last_modified")
    pre_dict["id"] = predata.get("id")
    # package local preset
    preset_local_dict = {}
    preset_local_dict["id"] = pre_dict["id"]
    preset_local_dict["_rule"] = pre_dict["_rule"]
    preset_local_dict["_meta"] = pre_dict["_meta"]
    return check_success, msg, preset_local_dict


def _get_predata_list(rawids):
    Predata = classing_model("aospredata")
    return_items = []
    rawids.reverse()
    for rawid in rawids:
        item = Predata.find({"id": rawid}, one=True)
        predata_ids = []
        locale_name_list = []
        package_name_list = []
        predata_ids.append(rawid)
        lc_pn = get_lc_pn_by_predataids(predata_ids)
        if lc_pn:
            for lc in lc_pn[0]:
                locale_name_list.append(lc.get("name"))
            for pn in lc_pn[1]:
                package_name_list.append(pn.get("package_name"))
            item["aoslocale"] = locale_name_list
            item["aospackage"] = package_name_list
        item["first_created"] = unixto_string(item.get("first_created"))
        item["last_modified"] = unixto_string(item.get("last_modified"))
        item.pop("_id", None)
        return_items.append(item)
    return return_items


@exception_handler()
def upload_predata(req):
    rawids = []
    Predata = classing_model("aospredata")
    Preset_Local = classing_model("preset_local")
    upload_success = []
    upload_failed = []
    if req.method == "POST":
        temp_strs = req.raw_post_data
        try:
            temp_dict = simplejson.loads(temp_strs)
        except ValueError as expt:
            _LOGGER.info("model delete api para except:%s", expt)
            return json_response_error(
                PARAM_ERROR,
                msg="json loads error,check parameters format")
        item_ids = temp_dict.get("items")
        for item in item_ids:
            rawids.append(int(item))
        if not rawids:
            return json_response_error(PARAM_ERROR, msg="id is empty")
        count = len(rawids)
        upload_place = temp_dict.get("server")
        if upload_place == _LOCAL:
            for rawid in rawids:
                count = count - 1
                # update status upload to local
                results = _package_one_predata(rawid, upload_place)
                if results[0]:
                    preset_local_dict = results[2]
                    now_time = now_timestamp()
                    Predata.update(
                        {"id": rawid},
                        {"is_upload_local": True,
                            "last_release_local": now_time,
                            "release": 2})
                    item_suc = Predata.find({"id": rawid}, one=True)
                    item_suc.pop("_id", None)
                    item_suc["last_modified"] = unixto_string(
                        item_suc["last_modified"])
                    item_suc["first_created"] = unixto_string(
                        item_suc["first_created"])
                    lc_pn = _get_local_package_preset(rawid)
                    item_suc["aoslocale"] = lc_pn.get("aoslocale")
                    item_suc["aospackage"] = lc_pn.get("aospackage")
                    upload_success.append(item_suc)
                    if not Preset_Local.find({"id": rawid}, one=True):
                        result = Preset_Local.insert(preset_local_dict)
                        _LOGGER.info(
                            "%d rawdata has put into local,result:%s",
                            rawid, result)
                    else:
                        upt_dict = {}
                        upt_dict["last_modified"] = now_timestamp()
                        upt_dict["_meta"] = preset_local_dict["_meta"]
                        upt_dict["_rule"] = preset_local_dict["_rule"]
                        Preset_Local.update({"id": rawid}, upt_dict)
                else:
                    return json_response_error(PARAM_ERROR, msg=results[1])
            # return_items = _get_predata_list(rawids)
            data = {}
            data["upload_success"] = upload_success
            data["upload_failed"] = upload_failed
            return json_response_ok(
                data, "there is %d not package success" % count)
        elif upload_place == _EC2:
            # 同步local中的数据到ec2
            Preset_Local = classing_model("preset_local")
            for rawid in rawids:
                item = Preset_Local.find({"id": rawid}, one=True, toarray=True)
                if not item:
                    item_failed = Predata.find({"id": rawid}, one=True)
                    item_failed.pop("_id", None)
                    item_failed["last_modified"] = unixto_string(
                        item_failed["last_modified"])
                    item_failed["first_created"] = unixto_string(
                        item_failed["first_created"])
                    lc_pn = _get_local_package_preset(rawid)
                    item_failed["aoslocale"] = lc_pn.get("aoslocale")
                    item_failed["aospackage"] = lc_pn.get("aospackage")
                    upload_failed.append(item_failed)
                    return json_response_error(
                        DATA_NOT_UPLOAD_TO_PRE,
                        msg="id:%d should upload to local first" % rawid)
                else:
                    results = _package_one_predata(rawid, upload_place)
                    if results[0]:
                        preset_ec2_dict = results[2]
                        now_time = now_timestamp()
                        if save_to_ec2(preset_ec2_dict):
                            Predata.update(
                                {"id": rawid},
                                {"is_upload_ec2": True,
                                    "last_release_ec2": now_time,
                                    "release": 0})
                            item_suc = Predata.find({"id": rawid}, one=True)
                            item_suc.pop("_id", None)
                            item_suc["last_modified"] = unixto_string(
                                item_suc["last_modified"])
                            item_suc["first_created"] = unixto_string(
                                item_suc["first_created"])
                            lc_pn = _get_local_package_preset(rawid)
                            item_suc["aoslocale"] = lc_pn.get("aoslocale")
                            item_suc["aospackage"] = lc_pn.get("aospackage")
                            upload_success.append(item_suc)
                    else:
                        json_response_error(PARAM_ERROR, msg=results[1])
            # return_items = _get_predata_list(rawids)
            data = {}
            data["upload_success"] = upload_success
            data["upload_failed"] = upload_failed
            return json_response_ok(
                data, msg="there is %d not package success" % count)
        else:
            return json_response_error(
                PARAM_ERROR, msg="UNKNOWN UPLOAD PLACE")
    else:
        return json_response_error(
            METHOD_ERROR, msg="http method error")


def export_predata(req):
    Preset_Local = classing_model("preset_local")
    rawids = []
    zip_file_name = "data.zip"
    if req.method == "GET":
        temp_dict = req.GET
        if temp_dict:
            ids = temp_dict.get("id")
            strs_id = ids.split(',')
            for sid in strs_id:
                rawids.append(int(sid))
        if rawids:
            mf = StringIO.StringIO()
            with zipfile.ZipFile(mf, 'w') as myzip:
                for rawid in rawids:
                    rawid = int(rawid)
                    preset_local_dict = {}
                    item = Preset_Local.find({"id": rawid}, one=True)
                    if item:
                        preset_local_dict = item
                    else:
                        results = _package_one_predata(rawid, _LOCAL)
                        if results[0]:
                            preset_local_dict = results[2]
                        else:
                            _LOGGER.error("export data error: %s" % results[1])
                    json_obj = preset_local_dict.get("_meta")
                    file_name = "preset_%d.json" % rawid
                    simplejson.dump(json_obj, mf, indent=4)
                    myzip.writestr(file_name, mf.getvalue())
            respone = HttpResponse(mf.getvalue(), mimetype="application/zip")
            respone["Content-Disposition"] = "attachment; "\
                "filename=%s" % zip_file_name
            return respone
        else:
            return json_response_error("no ids find")
    else:
        return json_response_error(
            METHOD_ERROR, msg="http method error")


def export_predata_by_rule(req):
    if req.method == "GET":
        filters = get_export_filters()
        return json_response_ok(filters, "test version")
    else:
        return json_response_error(METHOD_ERROR, "http method error")


@exception_handler()
def export_byrule(req):
    if req.method == "GET":
        Preset_Local = classing_model("preset_local")
        zip_file_name = "data.zip"
        platform = req.GET.get("platform")
        package = req.GET.get("package")
        source = req.GET.get("source")
        version_code = req.GET.get("version_code")
        if version_code:
            try:
                version_code = int(version_code)
            except:
                raise ValueError
        locales = req.GET.get("locale")
        locale_list = []
        if locales:
            locale_list = locales.split('|')
        mf = StringIO.StringIO()
        if locale_list:
            with zipfile.ZipFile(mf, mode='w') as zf:
                for locale in locale_list:
                    cond = {}
                    if platform:
                        cond["_rule.os"] = platform
                    if package:
                        cond["_rule.packages"] = package
                    if source:
                        cond["_rule.sources"] = {
                            "$in": [source, All_FLAG, DEFAULT_SOURCE]}
                    if locale:
                        cond["_rule.locales"] = locale
                    if version_code:
                        cond["$or"] = [
                            {"_rule.min_version": {"$lte": version_code},
                                "_rule.max_version": {"$gte": version_code}},
                            {"_rule.min_version": 0, "_rule.max_version": 0}]
                    item = Preset_Local.find(cond, one=True)
                    if item:
                        file_name = "preload_%s.json" % locale
                        preset_dict = item.get("_meta")
                        simplejson.dump(preset_dict, mf, indent=4)
                        zf.writestr(file_name, mf.getvalue())
            if mf.getvalue():
                respone = HttpResponse(
                    mf.getvalue(), mimetype="application/zip")
                respone["Content-Disposition"] = "attachment; "\
                    "filename=%s" % zip_file_name
                return respone
            else:
                return json_response_error(
                    PARAM_ERROR, msg="no data find")
        else:
            return json_response_error(
                PARAM_ERROR, msg="must chose one more locale")
    else:
        return json_response_error(METHOD_ERROR, "ttp method error")
