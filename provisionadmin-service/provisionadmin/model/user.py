# -*- coding: utf-8 -*-
import logging
from provisionadmin.utils.common import md5_string
from provisionadmin.model.base import ModelBase
from provisionadmin.utils.common import now_timestamp

_LOGGER = logging.getLogger("model")


class UserLog(ModelBase):
    db = 'user'
    collection = 'userlog'

    @classmethod
    def new(cls, uid, user_name, perm_name):
        instance = cls()
        instance.uid = uid
        instance.user_name = user_name
        instance.perm_name = perm_name
        instance.modified = now_timestamp()
        return instance

    @classmethod
    def save_log(cls, instance):
        return cls.save(instance, check_unique=False, extract=False)

    @classmethod
    def search_log_info(cls, cond={}, fields={}, toarray=False):
        return cls.find(cond, fields, toarray=toarray)


class Department(ModelBase):
    db = 'user'
    collection = 'departments'

    @classmethod
    def find_deparments(cls, cond, toarray=True):
        return cls.find(cond, toarray=toarray)


class User(ModelBase):
    db = 'user'
    collection = 'user'
    required = ('user_name', 'password')
    unique = ('user_name',)
    optional = (
        ('is_active', True),
        ('is_superuser', False),
        ('group_id', []),
        ('permission_list', []),
        ('last_login', now_timestamp),
        ('department', ''),
        ('mark', '')
    )

    @classmethod
    def new(cls, user_name, password='', is_active=True, department='',
            is_superuser=False, group_id=[], permission_list=[], mark=''):
        '''
        create user instance
        '''
        instance = cls()
        instance.user_name = user_name
        # if password: 密码已经在前端md5加密
        #  instance.password_hash = User.calc_password_hash(password)
        instance.password = password
        instance.is_active = is_active
        instance.is_superuser = is_superuser
        instance.group_id = group_id
        instance.permission_list = permission_list
        instance.created = instance.last_login = now_timestamp()
        instance.modified = now_timestamp()
        instance.total_login = 1
        instance.department = department
        instance.mark = mark
        return instance

    @classmethod
    def save_user(cls, instance):
        return cls.save(instance, check_unique=False)

    @classmethod
    def update_user(cls, cond, upt_dict):
        return cls.update(cond, upt_dict)

    @classmethod
    def find_users(cls, cond, fields={}, toarray=True):
        return cls.find(cond, fields, toarray=toarray)

    @classmethod
    def find_one_user(cls, cond, toarray=True):
        users = cls.find(cond, toarray=toarray)
        if users:
            return users[0]
        else:
            return None

    @classmethod
    def del_user(cls, ids):
        for uid in ids:
            user = cls.find_users({"_id": uid})
            if user:
                cls.remove({"_id": uid})
                _LOGGER.info("remove group id %d" % uid)
                ids.remove(uid)
            else:
                _LOGGER.info("group id %d is not exist" % uid)
        return ids

    @classmethod
    def calc_password_hash(cls, password):
        return unicode(md5_string(password))

    @classmethod
    def change_password(cls, new_password):
        cls.password = User.calc_password_hash(new_password)
        cls.modified = now_timestamp()

    @classmethod
    def change_group(cls, new_group_id):
        cls.group_id = new_group_id
        cls.modified = now_timestamp()

    @classmethod
    def change_permission(cls, new_permission_list):
        cls.permission_list = new_permission_list
        cls.modified = now_timestamp()

    @classmethod
    def change_active(cls, new_active_status):
        cls.is_active = new_active_status
        cls.modified = now_timestamp()

    @classmethod
    def _get_group_list(cls, array=[]):
        group_list = []
        if array:
            for group_id in array:
                groups = Group.find_group({"_id": group_id})
                group_list = group_list + groups
            return group_list
        else:
            return []

    @classmethod
    def get_filters(cls):
        '''
        not used in this version 1.4.3
        '''
        all_groups = []
        all_dict = {"display_value": "All", "value": "", "children": {}}
        all_children_dict = {"name": "role", "items": []}
        filters = {"name": "department", "items": []}
        filters["items"].append(all_dict)
        department_list = Department.find_deparments({})
        if not department_list:
            return []
        all_children_dict["items"].append(
            {"display_value": "All", "value": ""})
        for department in department_list:
            department_children = {"name": "role", "items": []}
            department_dict = {
                "display_value": "", "value": "", "children": {}}
            department_name = department.get("name")
            department_alias = department.get("alias")
            role_list = User._get_group_list(department.get("groups"))
            if not role_list:
                continue
            department_children["items"].append(
                {"display_value": "All", "value": ""})
            for role in role_list:
                role_dict = {
                    "display_value": role.get("alias"),
                    "value": role.get("group_name")}
                if role_dict not in all_groups:
                    all_groups.append(role_dict)
                department_children["items"].append(role_dict)
            department_dict["display_value"] = department_alias
            department_dict["value"] = department_name
            department_dict["children"] = department_children
            filters["items"].append(department_dict)
        for group in all_groups:
            group_dict = {
                "display_value": group.get("display_value"),
                "value": group.get("value")}
            all_children_dict["items"].append(group_dict)
        all_dict["children"] = all_children_dict
        return filters

    @classmethod
    def get_departments(cls, department_name="", role_ids=[]):
        department_list = Department.find_deparments({})
        '''not used in v1.4.3'''
        if not department_list:
            return []
        dplist = []
        for department in department_list:
            item = {}
            item["display_value"] = department.get("alias")
            item["value"] = department.get("name")
            item["roles"] = []
            roles = User._get_group_list(department.get("groups"))
            for role in roles:
                if department.get("name") == department_name and \
                        role.get("_id") in role_ids:
                    role_dict = {
                        "display_value": role.get("alias"),
                        "value": role.get("group_name"),
                        "selected": True}
                else:
                    role_dict = {
                        "display_value": role.get("alias"),
                        "value": role.get("group_name"),
                        "selected": False}
                item["roles"].append(role_dict)
            dplist.append(item)
        return dplist

    @classmethod
    def get_groups_roles(cls, department_names=[], role_ids=[], filters=False):
        department_list = Department.find_deparments({})
        role_list = Group.find_group({})
        admin_group = 2
        if not department_list:
            return None
        dplist = []
        rolist = []
        if filters:
            dplist.append({"display_value": "All", "value": ""})
            rolist.append({"display_value": "All", "value": ""})
        for department in department_list:
            dp_dict = {
                "display_value": department.get("alias"),
                "value": department.get("name")}
            if not filters:
                if department.get("alias") in department_names:
                    dp_dict["selected"] = True
                else:
                    dp_dict["selected"] = False
            dplist.append(dp_dict)
        for role in role_list:
            role_dict = {
                "display_value": role.get("alias"),
                "value": role.get("group_name")}
            if not filters:
                if role.get("_id") in role_ids:
                    role_dict["selected"] = True
                else:
                    role_dict["selected"] = False
            if role.get("_id") != admin_group:
                rolist.append(role_dict)
        return dplist, rolist

    @classmethod
    def get_all_country_managers(cls):
        cm_list = []
        COUNTRY_MANAGER_GROUP_ID = 3
        user_list = User.find_users({})
        for user in user_list:
            if COUNTRY_MANAGER_GROUP_ID in user.get("group_id"):
                cm_list.append(user.get("user_name"))
        return cm_list

    @classmethod
    def get_country_info(cls, uid):
        dplist = []
        admin_group = 2
        user = User.find_one_user({"_id": uid})
        department_list = Department.find_deparments({})
        if admin_group in user.get("group_id"):
            for department in department_list:
                dplist.append(department.get("alias"))
        else:
            departments = user.get("department")
            for department in departments:
                departs = Department.find_deparments({"name": department})
                if departs:
                    dep = departs[0]
                    dplist.append(dep.get("alias"))
        return list(set(dplist))

    @classmethod
    def get_charge_info(cls, department_name):
        cond1 = {"department": department_name, "group_id": 5}
        fields = {"user_name": 1}
        chargers = User.find_users(cond1, fields)
        cond2 = {"department": department_name, "group_id": 6}
        translators = User.find_users(cond2, fields)
        cond3 = {"department": department_name, "group_id": 3}
        country_pm = User.find_users(cond3, fields)
        return chargers, translators, country_pm

    @classmethod
    def get_admin_email(cls):
        admin_group = 2
        mail_list = []
        cond = {"group_id": admin_group}
        fields = {"user_name": 1, "_id": 0}
        users = User.find_users(cond, fields)
        if users:
            for user in users:
                mail_list.append(user.get("user_name"))
        return mail_list

    @classmethod
    def get_translator_email(cls, array=[]):
        mail_list = []
        if array:
            for uid in array:
                user = User.find_one_user({"_id": uid})
                mail_list.append(user.get("user_name"))
        return mail_list

    @classmethod
    def get_department_by_id(cls, uid):
        user = User.find_one_user({"_id": uid})
        if user:
            return user.get("department")
        else:
            return None


class Group(ModelBase):
    db = 'user'
    collection = 'groups'
    required = ('group_name',)
    unique = ('group_name',)
    optional = (('permission_list', []),)

    @classmethod
    def new(cls, group_name, permission_list=[]):
        """
        creat group instance
        """
        instance = cls()
        instance.group_name = group_name
        instance.alias = group_name
        instance.permission_list = permission_list
        instance.modified = now_timestamp()
        return instance

    @classmethod
    def save_group(cls, instance):
        return cls.save(instance, check_unique=False, extract=False)

    @classmethod
    def update_group(cls, cond, upt_dict):
        return cls.update(cond, upt_dict)

    @classmethod
    def find_group(cls, cond, toarray=True):
        return cls.find(cond, toarray=True)

    @classmethod
    def find_one_group(cls, cond, toarray=True):
        groups = cls.find(cond, toarray)
        if groups:
            return groups[0]
        else:
            return None

    @classmethod
    def del_group(cls, ids):
        for gid in ids:
            group = cls.find_group({"_id": gid})
            if group:
                cls.remove({"_id": gid})
                users_in_group = User.find_users({"group_id": gid})
                if users_in_group:
                    for user in users_in_group:
                        glist = user.get("group_id")
                        glist.remove(gid)
                        User.update_user(
                            {"_id": user["_id"]}, {"group_id": glist})
                        _LOGGER.info(
                            "remove group id:%d from user %d" %
                            (gid, user["_id"]))
                ids.remove(gid)
            else:
                _LOGGER.info("group id %d is not exist" % gid)
        return ids

    @classmethod
    def change_permission(cls, new_permission_list):
        cls.permission_list = new_permission_list
        cls.modified = now_timestamp()


class Model(ModelBase):
    db = 'user'
    collection = 'models'

    @classmethod
    def find_models(cls, cond, toarray=True):
        return cls.find(cond, toarray=toarray)

    @classmethod
    def find_one_model(cls, cond, toarray=True):
        models = cls.find(cond, toarray=toarray)
        if models:
            return models[0]
        else:
            return None


class App(ModelBase):
    db = 'user'
    collection = 'apps'

    @classmethod
    def find_apps(cls, cond, toarray=True):
        return cls.find(cond, toarray=toarray)

    @classmethod
    def find_one_app(cls, cond, toarray=True):
        apps = cls.find(cond, toarray=toarray)
        if apps:
            return apps[0]
        else:
            return None


class Permission(ModelBase):
    db = 'user'
    collection = 'permission'
    required = ('perm_type', 'perm_name', 'app_label', 'model_label',
                'container', 'action')

    @classmethod
    def new(cls, perm_type, perm_name, app_label, model_label, container,
            action):
        '''
        create permission instance
        '''
        instance = cls()
        instance.perm_type = perm_type
        instance.perm_name = perm_name
        instance.app_label = app_label
        instance.model_label = model_label
        instance.container = container
        instance.action = action
        return instance

    @classmethod
    def save_perm(cls, instance):
        return cls.save(instance, check_unique=False, extract=False)

    @classmethod
    def find_perm(cls, cond, toarray=True):
        return cls.find(cond, toarray=toarray)

    @classmethod
    def find_one_perm(cls, cond, toarray=True):
        '''
        return one detail permission
        '''
        perms = cls.find(cond, toarray=toarray)
        if perms:
            return perms[0]
        else:
            return None

    @classmethod
    def del_perm(cls, ids):
        '''
        delete permission by id array
        '''
        for pid in ids:
            perm = cls.find_perm({"_id": pid})
            if perm:
                cls.remove({"_id": pid})
                users_has_perm = User.find_users({"permission_list": pid})
                if users_has_perm:
                    for user in users_has_perm:
                        plist = user.get("permission_list")
                        plist.remove(pid)
                        User.update_user(
                            {"_id": user["_id"]}, {"permission_list": plist})
                        _LOGGER.info(
                            "remove group id:%d from user %d" %
                            (pid, user["_id"]))
                group_has_perm = Group.find_group({"permission_list": pid})
                if group_has_perm:
                    for group in group_has_perm:
                        plist = group.get("permission_list")
                        plist.remove(pid)
                        Group.update_group(
                            {"_id": group["_id"]}, {"permission_list": plist})
                        _LOGGER.info(
                            "remove Permission id:%d from group %d" %
                            (pid, group["_id"]))
                ids.remove(pid)
            else:
                _LOGGER.info("group id %d is not exist" % pid)
        return ids

    @classmethod
    def get_perms_by_uid(cls, uid, perm_type="model"):
        '''
        get permission by user id
        returns default "model" type
        '''
        perm_list = []
        user = User.find_one_user({"_id": int(uid)})
        if user:
            if user.get("is_superuser"):
                return Permission.find_perm({"perm_type": perm_type})
            else:
                perm_list = user.get("permission_list")
                gids = user.get("group_id")
                if gids:
                    for gid in gids:
                        groups = Group.find_group({"_id": gid})
                        if groups:
                            group = groups[0]
                            perm_list = perm_list + group.get(
                                "permission_list")
                    perm_list = list(set(perm_list))
                return Permission.get_perms_by_ids(perm_list, perm_type)
        else:
            return None

    @classmethod
    def get_perms_by_ids(cls, pids, perm_type="model"):
        '''
        an internal function for getting permissions by id array
        '''
        permissions = []
        for pid in pids:
            perm = Permission.find_one_perm(
                {"_id": pid, "perm_type": perm_type})
            if perm:
                permissions.append(perm)
        return permissions

    @classmethod
    def _get_container_alias(cls, container):
        '''
        get the alias of container, it aims to display first title on menu
        '''
        cond = {"type": 0, "container_name": container}
        app_diff_cont = App.find_one_app(cond)
        if app_diff_cont:
            return app_diff_cont.get("container_alias")
        else:
            app_same_con = App.find_one_app({"type": 1, "app_name": container})
            if app_same_con:
                return app_same_con.get("app_alias")
            else:
                return "none-alias"

    @classmethod
    def _order_container(cls, containers):
        '''
        order the containers that will show on menu
        '''
        temp_list = []
        temp_dict = {}
        for container in containers:
            cont = App.find_one_app({"container_name": container})
            # check  container name is exist
            if cont:
                order_index = cont.get("order")
                temp_dict[order_index] = container
            else:
                app = App.find_one_app({"app_name": container})
                order_index = app.get("order")
                temp_dict[order_index] = container
        keys = temp_dict.keys()
        keys.sort()
        for key in keys:
            temp_list.append(temp_dict[key])
        return temp_list

    @classmethod
    def _order_models(cls, models):
        '''order the model menu order'''
        modelname_list = []
        temp_dict = {}
        for modelname in models:
            model_dict = Model.find_one_model({"model_name": modelname})
            order_index = model_dict.get("menu")
            temp_dict[order_index] = modelname
        keys = temp_dict.keys()
        keys.sort()
        for key in keys:
            modelname_list.append(temp_dict[key])
        return modelname_list

    @classmethod
    def _get_app_by_name(cls, app_name):
        return App.find_one_app({"app_name": app_name})

    @classmethod
    def _get_model_by_name(cls, model_name):
        return Model.find_one_model({"model_name": model_name})

    @classmethod
    def init_menu_list(cls, uid):
        '''
        init menu for user by uid
        it is dynamic, it is combined with user's permissions
        '''
        perms = Permission.get_perms_by_uid(uid)
        if perms:
            menu = []
            containers = []
            apps = []
            models = []
            for perm in perms:
                containers.append(perm.get('container'))
            containers = list(set(containers))
            if not containers:
                return None
            containers = Permission._order_container(containers)
            # order the containers
            con_index = 0
            for container in containers:
                container_alias = Permission._get_container_alias(container)
                # get alias of container
                menu.append(
                    {'module': container,
                     'display': container_alias,
                     'items': []})
                apps[:] = []
                for perm in perms:
                    if perm.get('container') == container:
                        apps.append(perm.get('app_label'))
                apps = list(set(apps))
                if not apps:
                    return None
                app_index = 0
                for app in apps:
                    app_dict = Permission._get_app_by_name(app)
                    match_type = app_dict.get("type")
                    models[:] = []
                    for perm in perms:
                        if perm.get('app_label') == app:
                            model_name = perm.get('model_label')
                            model_dict = Permission._get_model_by_name(
                                model_name)
                            if model_dict.get("menu") != 0:
                                models.append(model_name)
                    models = list(set(models))
                    models = Permission._order_models(models)
                    # get alias of app
                    if match_type == 0:
                        # if app_name is not equal with container
                        app_alias = app_dict.get("app_alias")
                        menu[con_index]['items'].append(
                            {'module': app, 'display': app_alias, 'items': []})
                        for model in models:
                            temp = Model.find_one_model({"model_name": model})
                            model_alias = temp.get("model_alias")
                            temp = {
                                'model': model,
                                'display': model_alias,
                                'url': container + '/' + app + '/' + model}
                            menu[con_index]['items'][app_index][
                                'items'].append(temp)
                    else:
                        for model in models:
                            temp = Model.find_one_model({"model_name": model})
                            model_alias = temp.get("model_alias")
                            temp_dict = {
                                'model': model,
                                'display': model_alias,
                                'url': app + '/' + model}
                            menu[con_index]['items'].append(temp_dict)
                    app_index = app_index + 1
                con_index = con_index + 1
            return menu
        else:
            return None

    @classmethod
    def init_perms_list(cls, uid):
        '''
        return values like below:
         [{
           "model":"xxx",
           "action":[add,edit]
            } ]
        '''
        assert uid
        permissions = []
        models = []
        perms = Permission.get_perms_by_uid(uid)
        for perm in perms:
            model_name = perm.get("model_label")
            models.append(model_name)
            models = list(set(models))
        for model in models:
            temp = {}
            temp["model"] = model
            for perm in perms:
                model_label = perm.get("model_label")
                action = perm.get("action")
                if model == model_label:
                    temp.setdefault("action", []).append(action)
            permissions.append(temp.copy())
        return permissions

    @classmethod
    def init_features(cls, uid):
        '''
        some feature function
        return like this:
            {
                "features":[a,b]
                }
        '''
        feature = []
        perms = Permission.get_perms_by_uid(uid, "feature")
        for perm in perms:
            feature.append(perm.get("perm_name"))
        return feature

    @classmethod
    def init_menu(cls, uid):
        '''
        combined the result of three all,
        it is used for loggin api
        '''
        assert uid
        user = User.find_one_user({"_id": int(uid)})
        if user:
            result = {}
            menu = Permission.init_menu_list(uid)
            permissions = Permission.init_perms_list(uid)
            features = Permission.init_features(uid)
            item1 = {"menu": menu}
            item2 = {"permissions": permissions}
            item3 = {"features": features}
            total_login = user.get("total_login")
            item4 = {}
            if total_login == 2:
                item4["need_changepwd"] = True
            else:
                item4["need_changepwd"] = False
            result.update(item1)
            result.update(item2)
            result.update(item3)
            result.update(item4)
            return result
        else:
            return None

    @classmethod
    def _get_group_permlist(cls, uid):
        permlist = []
        users = User.find_users({"_id": uid})
        if users:
            user = users[0]
            gids = user.get("group_id")
            for gid in gids:
                groups = Group.find_group({"_id": gid})
                group = groups[0]
                permlist = permlist + group.get("permission_list")
        return permlist

    @classmethod
    def user_perm_list(cls, uid, grant_id=0, group_id=0):
        '''
        grant user or group Permissions,but can not do it at the same time
        '''
        FLAGE = ""
        GROUP_USER_PERMS = []
        perm_list = Permission.get_perms_by_uid(uid)
        grant_perm_ids = []
        if grant_id:
            grant_perm_list = Permission.get_perms_by_uid(grant_id)
            FLAGE = "user_role"
            if grant_perm_list:
                for perm in grant_perm_list:
                    grant_perm_ids.append(perm.get("_id"))
            GROUP_USER_PERMS = Permission._get_group_permlist(grant_id)
        if group_id:
            FLAGE = "group_role"
            groups = Group.find_group({"_id": group_id})
            if groups:
                grant_perm_ids = groups[0].get("permission_list")
        app_list = []
        if not perm_list:
            return []
        for perm in perm_list:
            action_dict = {"id": perm.get("_id"),
                           "name": perm.get("action")}
            if perm.get("_id") in grant_perm_ids:
                action_dict["checked"] = True
                print perm.get("_id")
                print GROUP_USER_PERMS
                if FLAGE == "user_role" and \
                        perm.get("_id") in GROUP_USER_PERMS:
                    print perm.get("_id") in GROUP_USER_PERMS
                    action_dict["disabled"] = True
            else:
                action_dict["checked"] = False
            if not app_list:
                app_dict = {"title": "", "items": []}
                app_dict["title"] = perm.get("app_label").title()
                model_dict = {"model": "", "actions": []}
                model_dict["model"] = perm.get("model_label")
                model_dict["actions"].append(action_dict)
                app_dict["items"].append(model_dict)
                app_list.append(app_dict)
            else:
                app_name = perm.get("app_label")
                model_name = perm.get("model_label")
                for app in app_list:
                    if app["title"] == app_name.title():
                        for model in app["items"]:
                            if model["model"] == model_name:
                                model["actions"].append(action_dict)
                                break
                        else:
                            model_dict = {"model": "", "actions": []}
                            model_dict["model"] = model_name
                            model_dict["actions"].append(action_dict)
                            app["items"].append(model_dict)
                        break
                else:
                    app_dict = {"title": "", "items": []}
                    app_dict["title"] = perm.get("app_label").title()
                    model_dict = {"model": "", "actions": []}
                    model_dict["model"] = perm.get("model_label")
                    model_dict["actions"].append(action_dict)
                    app_dict["items"].append(model_dict)
                    app_list.append(app_dict)
        return app_list

    @classmethod
    def user_perm_feature(cls, uid, grant_id=0, group_id=0):
        features = []
        grant_feature_ids = []
        FLAGE = ""
        GROUP_USER_PERMS = []
        feature_list = Permission.get_perms_by_uid(uid, "feature")
        if grant_id:
            FLAGE = "user_role"
            GROUP_USER_PERMS = Permission._get_group_permlist(grant_id)
            grant_feature_list = Permission.get_perms_by_uid(
                grant_id, "feature")
            if grant_feature_list:
                for item in grant_feature_list:
                    grant_feature_ids.append(item.get("_id"))
        if group_id:
            groups = Group.find_group({"_id": group_id})
            if groups:
                grant_feature_ids = groups[0].get("permission_list")
        if not feature_list:
            return []
        for feature in feature_list:
            item = {"id": feature.get("_id"),
                    "name": feature.get("perm_name")}
            if feature.get("_id") in grant_feature_ids:
                item["checked"] = True
                if FLAGE == "user_role" and \
                        feature.get("_id") in GROUP_USER_PERMS:
                    item["disabled"] = True
            else:
                item["checked"] = False
            features.append(item)
        return features
