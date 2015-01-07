# -*- coding:utf-8 -*-
# @Author : Xiang Shu
# Email: xshu@bainainfo.com
'''
preload API
'''
import logging
import sys
import random

from django.views.decorators.http import require_GET
from provision.service.exceptions import InternalError, ParamError
from provision.service.views import response_json, OPERATORS, OTHER
from provision.utils.json import json_response_error, json_response_ok
from provision.utils.respcode import DATA_NOTFOUND, LOCALE_ONLY
from provision.service.errors import (parameter_error, internal_server_error,
                                      resource_not_modified)
from provision.decorator import match_location
from provision.service.models import sharedb, desktopdb, presetdb
from provision.service.utils.content import (RULE_ORIGINIZE, DESKTOP_PARAS,
                                             PRESET_PARAS, SHARE_PARAS)
from provision.service.utils.common_op import (get_valid_params, get_cond,
                                               filter_rule, get_smart_locale)

_LOGGER = logging.getLogger('provision.service')

DEFAULT_SOURCE = 'ofw'
DEFAULT_ACTION = 'false'
ALL_FLAG = 'all_condition'


MODULES = {
    'desktop': {
        'paras': DESKTOP_PARAS,
        'fields': ('pn', 'appvc', 'no', 'chn', 'lc'),
        'db_conn': desktopdb,
        'data_field': 'data',
        'data_type': list
    },
    'share': {
        'paras': SHARE_PARAS,
        'fields': ('pn', 'appvc', 'no', 'chn', 'lc'),
        'db_conn': sharedb,
        'data_field': '_meta',
        'data_type': dict
    }
}


def get_module(query_dict, module_name):
    '''
    get module data(speeddial, share) by client params with rule
    '''
    module_option = MODULES.get(module_name)
    try:
        args = get_valid_params(query_dict, module_option['paras'])
    except Exception, e:
        _LOGGER.warn('check %s\'s parameter exception![%s]' % (module_name, e))
        return {'data': module_option['data_type'](),
                'first_created': None,
                'last_modified': None}

    if args['no'] not in OPERATORS:
        args['no'] = OTHER
    cond = get_cond(args, RULE_ORIGINIZE, module_option['fields'])
    _LOGGER.debug(cond)
    data_infos = module_option['db_conn'].get_data(cond)
    if not data_infos:
        return {'data': module_option['data_type'](),
                'first_created': None,
                'last_modified': None}
    _LOGGER.debug(data_infos)
    data_infos = filter_rule(data_infos,
                             {'sources': args['chn'],
                              'locales': args['lc'],
                              'operators': args['no']},
                             {'min_version': True})
    if len(data_infos):
        return {'data': data_infos[module_option['data_field']],
                'first_created': data_infos.get('first_created'),
                'last_modified': data_infos.get('last_modified')}
    return {'data': module_option['data_type'](),
            'first_created': None,
            'last_modified': None}


def get_preset(cond, no_default):
    '''
    get preset data by condition
    '''
    try:
        presets = presetdb.get_presets(cond)
        _LOGGER.debug(presets)
        preset_num = len(presets)
        if preset_num >= 2:
            if preset_num > 2:
                _LOGGER.warning('preset data error')
            # here we modify random strategy to sorted by modified_time
            '''
            # old code for comparision
            rand = random.randint(0, 1)
            preset = presets[rand]
            '''
            presets.sort(key=lambda x: x.get('last_modified'), reverse=True)
            preset = presets[0]
            preset['strategy'] = preset['strategies'][0]
        elif preset_num == 1:
            preset = presets[0]
            strategies = preset['strategies']
            strategies_num = len(strategies)
            if strategies_num >= 2:
                if strategies_num > 2:
                    _LOGGER.warning('preset strategy error')
                rand = random.randint(0, 1)
                preset['strategy'] = strategies[rand]
            elif len(strategies) == 1:
                preset['strategy'] = strategies[0]
            else:
                _LOGGER.error('Preset Strategy is none')
                preset['strategy'] = None
        elif preset_num == 0:
            preset = None
            if no_default:
                cond['sources'] = DEFAULT_SOURCE
                preset = presetdb.get_preset(cond)
                if preset:
                    preset['strategy'] = preset['strategies'][0]
        _LOGGER.debug(preset)
        if isinstance(preset, dict) and 'strategies' in preset:
            del preset['strategies']
    except Exception, e:
        _LOGGER.exception(e)
        raise InternalError('get_preset error')

    return preset


def get_preset_by_locale(args, no_default, smart_locale):
    '''
    get preset data by condition
    '''
    cond = {
        'os': args['os'],
        'package': args['pn'],
        'sources': {'$in': [args['chn'], ALL_FLAG]},
        'locale': smart_locale,
        '$or': [
            {'min_version': {'$lte': args['appvc']},
                'max_version': {'$gte': args['appvc']}},
            {'min_version': 0, 'max_version': 0}
        ]
    }
    _LOGGER.debug(cond)

    preset = get_preset(cond, no_default)
    return preset


@require_GET
@match_location
def show_preset_v2(request, country=None, svr_locale=None):
    '''
    preload API version 2
    get preload data by client params

    Logic order:
        1. check HTTP parameter, ang get the valid parameter
        2. check country_code, get smart_locale
        3. create condition
        4. get preset data by condition
        5. get desktop/share data by condition
        6. HTTP response by data

    Request URL: api/2/provision.json

    HTTP Method: GET

    Parameters:
        - os: os type，eg: android
        - pn: package name
        - chn: channel name, eg: ofw
        - lc: locale, eg: en_US
        - appvc: app version code, eg: 354
        - appvn: app version name, eg: 11.1.2
        - nd: no default flag
        - debug: debug flag

    Return:
        1. found preload data which was updated
            {
                "status": 0
                "data":{
                    ...
                }
            }
        2. not found preload data
            {
                "status": 4,
                "data":{
                    "smart_locale": "en_US"
                }
            }
        3. found preload data which was not updated
            {
                "status": 10,
                "data":{
                    "smart_locale": "en_US"
                }
            }
    '''
    data = request.GET
    # for debug
    is_debug = data.get('debug')
    try:
        args = get_valid_params(data, PRESET_PARAS)
        no_default = args['nd']
    except Exception, e:
        _LOGGER.warn('check preset\'s parameter exception![%s]' % e)
        if isinstance(e, ParamError):
            _LOGGER.error("URL:%s Exception:%s"
                          % (request.build_absolute_uri(), e))
            return parameter_error(request, e)
        if isinstance(e, InternalError):
            return internal_server_error(request, e, sys.exc_info())

    smart_locales = get_smart_locale(country, svr_locale, args.get('lc'))
    preset = None
    if len(smart_locales) > 1:
        possible_locale, recommended_locale = (smart_locales[0],
                                               smart_locales[1])
        try:
            preset = get_preset_by_locale(args, no_default, possible_locale)
            smart_locale = recommended_locale\
                if not preset else possible_locale
        except Exception, e:
            smart_locale = recommended_locale
    else:
        smart_locale = smart_locales[0]

    _LOGGER.info('smart locale:%s' % smart_locale)

    if not preset:
        try:
            preset = get_preset_by_locale(args, no_default, smart_locale)
        except Exception, e:
            return internal_server_error(request, e, sys.exc_info())

        if not preset:
            if smart_locale:
                ext_msg = {'smart_locale': smart_locale}
            else:
                ext_msg = ''
            return json_response_error(DATA_NOTFOUND, ext_msg)

    preset.update({"smart_locale": smart_locale})

    # get desktop data
    args.update({"lc": smart_locale})
    try:
        desktop_data = get_module(args, 'desktop')
        preset.update({"speeddials": desktop_data['data']})
    except Exception, e:
        return internal_server_error(request, e, sys.exc_info())

    # get share data
    try:
        share_data = get_module(args, 'share')
        preset.update({"shares": share_data['data']})
    except Exception, e:
        return internal_server_error(request, e, sys.exc_info())

    enable_response = preset.get('enable_response')
    if is_debug is None and args['appvc'] >= 354\
            and not enable_response\
            and not _has_modified(preset)\
            and not _has_modified(desktop_data)\
            and not _has_modified(share_data):
        ext_msg = {'smart_locale': smart_locale}
        return json_response_error(LOCALE_ONLY, ext_msg)

    if enable_response is not None:
        del preset['enable_response']
    if preset.get('first_created') is not None:
        del preset['first_created']
    if preset.get('last_modified') is not None:
        del preset['last_modified']

    # track preset id for statistics
    _LOGGER.info('[DolphinStat]fetch preset data of id[%s]', preset.get('id'))

    return json_response_ok(preset)


def _has_modified(check_dict):
    '''
    internal function, check if the module data has been modified
    '''
    first_created = check_dict.get('first_created')
    last_modified = check_dict.get('last_modified')
    if last_modified is not None:
        if first_created is not None and last_modified == first_created:
            return False
        else:
            return True

    return False


@require_GET
@match_location
def show_preset_v3(request, country=None, svr_locale=None):
    '''
    preload API version 3
    get preload data by client params

    Logic order:
        1. check HTTP parameter, ang get the valid parameter
        2. check country_code, get smart_locale
        3. create condition
        4. get preset data by condition
        5. get desktop(speeddial) data by condition
        6. HTTP response by data

    Not Implemented
    '''
    preset = {}
    return json_response_ok(preset)


@require_GET
def show_preset_v1(request):
    '''
    preload API version 1
    old API(deprecated), just for compatibility here

    Logic order:
        1. check HTTP parameter, ang get the valid parameter
        2. create condition
        3. get data by condition
        4. HTTP response by data

    Deprecated
    '''
    data = request.GET
    try:
        os = data.get('os', '').lower()
        package = data.get('pname')
        source = data.get('src', DEFAULT_SOURCE)
        locale = data.get('l')
        version = int(data.get('v', 0))
        no_default_str = data.get('nd', DEFAULT_ACTION).lower()
        bool_map = {
            'true': True,
            'false': False
        }
        no_default = bool_map[no_default_str]
    except Exception, e:
        _LOGGER.debug("URL:%s Exception:%s"
                      % (request.build_absolute_uri(), e))
        return parameter_error(request, e)
    try:
        cond = {
            'os': os,
            'package': package,
            'sources': {'$in': [source, ALL_FLAG]},
            'locale': locale,
            '$or': [
                {'min_version': {'$lte': version},
                    'max_version': {'$gte': version}},
                {'min_version': 0, 'max_version': 0}
            ]
        }
        _LOGGER.debug(cond)

        preset = get_preset(cond, no_default)
    except Exception, e:
        return internal_server_error(request, e, sys.exc_info())

    if not preset:
        return resource_not_modified('preset')

    enable_response = preset.get('enable_response')
    if enable_response is not None:
        del preset['enable_response']
    if preset.get('first_created') is not None:
        del preset['first_created']
    if preset.get('last_modified') is not None:
        del preset['last_modified']

    # track preset id for statistics
    _LOGGER.info('[DolphinStat]fetch preset data of id[%s]', preset.get('id'))
    return response_json(preset)
