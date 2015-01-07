# coding: utf-8
import logging
from provisionadmin.model.base import ModelBase
from provisionadmin.settings import MODELS
from provisionadmin.db.config import LOCAL_DB, CHINA_DB, EC2_DB
from provisionadmin.utils.common import now_timestamp
# from provisionadmin.utils.version_list import VERSION_LIST


_LOGGER = logging.getLogger("model")
_CHINA = "china"
_EC2 = "ec2"
_ANDROID = "android"
_IOS = "ios"
_DEFAULT_SOURCE = "ofw"


def _get_ids(child_ids, child_model, parent_model):
    parent_ids = []
    cond = {}
    Parent_Model = classing_model(str(parent_model))
    for child_id in child_ids:
        cond[child_model + ".id"] = child_id
        parents = Parent_Model.find(cond, toarray=True)
        for parent in parents:
            parent_ids.append(parent.get("id"))
    return list(set(parent_ids))


def get_lc_pn_by_predataids(predata_ids=[]):
    Predata = classing_model("aospredata")
    locale_list = []
    package_list = []
    Rule = classing_model("aosruledata")
    Locale = classing_model("aoslocale")
    Package = classing_model("aospackage")
    for predata_id in predata_ids:
        predata = Predata.find({"id": predata_id}, one=True)
        rule_dict = predata.get("aosruledata")
        rule = Rule.find({"id": rule_dict.get("id")}, one=True)
        if rule:
            locale_ids = rule.get("aoslocale")
            package_ids = rule.get("aospackage")
            for locale_id in locale_ids:
                locale_dict = Locale.find({"id": locale_id}, one=True)
                if locale_dict:
                    locale_dict.pop("_id", None)
                    locale_list.append(locale_dict)
            for package_id in package_ids:
                package_dict = Package.find({"id": package_id}, one=True)
                if package_dict:
                    package_dict.pop("_id", None)
                    package_list.append(package_dict)
    return locale_list, package_list


def get_ref_rule_preset(model_name, model_id):
    Predata = classing_model("aospredata")
    Rule = classing_model("aosruledata")
    rules = Rule.find({model_name: model_id}, toarray=True)
    ref_ids = []
    if rules:
        for rule in rules:
            ruleid = rule.get("id")
            presets = Predata.find({"aosruledata.id": ruleid}, toarray=True)
            if presets:
                for preset in presets:
                    presetid = preset.get("id")
                    ref_ids.append(presetid)
    return list(set(ref_ids))


def ref_get_presetdata(model_id, model_name, object_link=[]):
    Predata = classing_model("aospredata")
    predata_list = []
    length = len(object_link)
    cond = {}
    predata_ids = []
    if length == 1:
        cond[model_name + ".id"] = model_id
        predata_list = Predata.find(cond, toarray=True)
        if predata_list:
            for predata in predata_list:
                predata_ids.append(predata.get("id"))
    else:
        index = 0
        start_model = model_name
        next_ids = []
        next_ids.append(model_id)
        while index < length:
            next_ids = _get_ids(next_ids, start_model, object_link[index])
            start_model = object_link[index]
            index = index + 1
        predata_ids = next_ids
    return predata_ids


def check_in_ec2(rawid):
    item = EC2_DB.preset_ec2.find_one({"id": rawid})
    return True if item else False


def remove_from_ec2(rawid):
    print "remove"
    EC2_DB.preset_ec2.remove({"id": rawid})


def save_to_ec2(ec2_dict):
    rawid = ec2_dict.get("id")
    item = EC2_DB.preset.find_one({"id": rawid})
    if not item:
        insert_dict = {}
        insert_dict["id"] = ec2_dict["id"]
        insert_dict["_meta"] = ec2_dict["_meta"]
        insert_dict["_rule"] = ec2_dict["_rule"]
        insert_dict["first_created"] = now_timestamp()
        insert_dict["last_modified"] = now_timestamp()
        EC2_DB.preset.insert(insert_dict)
        _LOGGER.info("insert ec2 success")
        return True
    else:
        # update it
        upt_dict = {}
        upt_dict["_rule"] = ec2_dict["_rule"]
        upt_dict["_meta"] = ec2_dict["_meta"]
        upt_dict["last_modified"] = now_timestamp()
        upt_dict["first_created"] = item["first_created"]
        EC2_DB.preset.update({"id": rawid}, upt_dict)
        _LOGGER.info("update success")
        return True


def sync_db(server_name=None, predata_id=0):
    if not server_name:
        return False
    if not predata_id:
        return False
    local_data = LOCAL_DB.preset.find_one({"id": predata_id})
    if server_name == _CHINA:
        item = CHINA_DB.preset_cn.find_one({"id": predata_id})
        if not item:
            china_dict = {}
            china_dict["id"] = local_data["id"]
            china_dict["_meta"] = local_data["_meta"]
            china_dict["_rule"] = local_data["_rule"]
            china_dict["first_created"] = now_timestamp()
            china_dict["last_modified"] = now_timestamp()
            CHINA_DB.preset_cn.insert(china_dict)
            _LOGGER.info("%s insert success", server_name)
            return True
        else:
            # update it
            upt_dict = {}
            upt_dict["_rule"] = local_data["_rule"]
            upt_dict["_meta"] = local_data["_meta"]
            upt_dict["last_modified"] = now_timestamp()
            upt_dict["first_created"] = item["first_created"]
            CHINA_DB.preset_cn.update({"id": predata_id}, upt_dict)
            _LOGGER.info("%s update success", server_name)
            return True
    elif server_name == _EC2:
        item = EC2_DB.preset_ec2.find_one({"id": predata_id})
        if not item:
            insert_dict = {}
            insert_dict["id"] = local_data["id"]
            insert_dict["_meta"] = local_data["_meta"]
            insert_dict["_rule"] = local_data["_rule"]
            insert_dict["first_created"] = now_timestamp()
            insert_dict["last_modified"] = now_timestamp()
            EC2_DB.preset_ec2.insert(insert_dict)
            _LOGGER.info("%s insert success", server_name)
            return True
        else:
            # update it
            upt_dict = {}
            upt_dict["_rule"] = local_data["_rule"]
            upt_dict["_meta"] = local_data["_meta"]
            upt_dict["last_modified"] = now_timestamp()
            upt_dict["first_created"] = item["first_created"]
            EC2_DB.preset_cn.update({"id": predata_id}, upt_dict)
            _LOGGER.info("%s update success", server_name)
            return True
    else:
        _LOGGER.info("no such server_name")
        return False


def get_filters(params=[]):
    filter_list = []
    if not params:
        return []
    else:
        if "aoslocale" in params:
            locale_list = []
            locale_list.append({"display_value": "选择Locales", "value": ""})
            Locale = classing_model("aoslocale")
            locales = Locale.find({}, toarray=True)
            for local in locales:
                locale_dict = {
                    "display_value": local.get("name"),
                    "value": local.get("id")}
                locale_list.append(locale_dict)
            filter_dict = {}
            filter_dict["items"] = locale_list
            filter_dict["name"] = "aoslocale"
            filter_list.append(filter_dict)
        if "aospackage" in params:
            package_list = []
            package_list.append({"display_value": "选择项目名称", "value": ""})
            Package = classing_model("aospackage")
            packages = Package.find({}, toarray=True)
            for package in packages:
                package_dict = {
                    "display_value": package.get("title"),
                    "value": package.get("id")}
                package_list.append(package_dict)
            filter_dict = {}
            filter_dict["items"] = package_list
            filter_dict["name"] = "aospackage"
            filter_list.append(filter_dict)
        return filter_list


def _get_platform_list():
    platform_list = []
    Preset_Local = classing_model("preset_local")
    all_data = Preset_Local.find({}, toarray=True)
    if all_data:
        for item in all_data:
            rule_dict = item.get("_rule")
            platform_list.append(rule_dict.get("os"))
        return list(set(platform_list))
    else:
        return []


def _get_source_list(platform=_ANDROID):
    cond = {}
    source_list = []
    if platform:
        cond["_rule.os"] = platform
        Preset_Local = classing_model("preset_local")
        all_data = Preset_Local.find(cond, toarray=True)
        if all_data:
            for item in all_data:
                rule_dict = item.get("_rule")
                source_list = source_list + rule_dict.get("sources")
            return list(set(source_list))
        else:
            return []
    else:
        return []


def _get_package_list(platform=_ANDROID, source=_DEFAULT_SOURCE):
    cond = {}
    if platform:
        cond["_rule.os"] = platform
    if source:
        cond["_rule.sources"] = source
        Preset_Local = classing_model("preset_local")
        all_data = Preset_Local.find(cond, toarray=True)
        package_list = []
        if all_data:
            for item in all_data:
                rule_dict = item.get("_rule")
                package_list = package_list + rule_dict.get("packages")
            return list(set(package_list))
        else:
            return []
    else:
        return []


def _get_locale_list(platform=_ANDROID):
    Preset_Local = classing_model("preset_local")
    locale_list = []
    return_items = []
    cond = {}
    if platform:
        cond['_rule.os'] = platform
    all_data = Preset_Local.find(cond, toarray=True)
    if all_data:
        for item in all_data:
            rule_dict = item.get("_rule")
            locale_list = locale_list + rule_dict.get("locales")
        locale_list = list(set(locale_list))
        # locale_list = locale_list.sort()
        for locale in locale_list:
            locale_dict = {}
            locale_dict["display_value"] = locale
            locale_dict["value"] = locale
            return_items.append(locale_dict)
        return return_items
    else:
        return []


def get_export_filters():
    all_filters = {}
    filters = {"name": "platform", "items": []}
    platform_list = _get_platform_list()
    print platform_list
    for platform in platform_list:
        plat_children = {"name": "source", "items": []}
        platform_item = {"display_value": "", "value": "", "children": {}}
        source_list = _get_source_list(platform)
        for source in source_list:
            source_children = {"name": "package", "items": []}
            source_item = {
                "display_value": "", "value": "", "children": {}}
            package_list = _get_package_list(platform, source)
            all_package_dict = {"display_value": "All", "value": ""}
            source_children["items"].append(all_package_dict)
            for package in package_list:
                package_item = {"display_value": "", "value": ""}
                package_item["display_value"] = package
                package_item["value"] = package
                source_children["items"].append(package_item)
            source_item["display_value"] = source
            source_item["value"] = source
            source_item["children"] = source_children
            plat_children["items"].append(source_item)
        platform_item["display_value"] = platform
        platform_item["value"] = platform
        platform_item["children"] = plat_children
        filters["items"].append(platform_item)
    locales = _get_locale_list()
    all_filters["filters"] = filters
    all_filters["locales"] = locales
    return all_filters


def classing_model(model_name):
    '''
    type method can be used as a metaclass funtion, when a string "model_name"
    came, it can be return the class
    '''
    if MODELS.get(model_name):
        ATTRS = MODELS.get(model_name)
        return type(model_name, (ModelBase,), ATTRS)
    else:
        return None
