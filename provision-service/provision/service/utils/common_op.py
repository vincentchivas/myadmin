#!/usr/bin/env python
# -*- coding:utf-8 -*-
# coder yfhe
import logging
from provision.service.utils.content import ALL_FLAG, ALL_WEIGHT, MATCH_WEIGHT
from provision.service.exceptions import InternalError, ParamError


def get_logger(role):
    '''
    get logger
    '''
    matchs = {
        'service': 'provision.service',
        'db': 'provision.db',
    }
    return logging.getLogger(matchs[role])


_LOGGER = get_logger('service')


def get_cond(args, ORIGINIZE, fields):
    '''
    get condition for mongo
    '''
    cond = {}
    for key, value in args.items():
        if key in ORIGINIZE and value is not None and key in fields:
            match = ORIGINIZE[key]
            if not match[1]:
                cond.update(eval(match[0]))
            else:
                cond.update(eval(match[0] % (value, value))
                            if match[1] == 2 else eval(match[0] % value))
    return cond


def filter_gray_level(sections, mark):
    '''
    filter gray level
    '''
    result = []
    for item in sections:
        min_mark = item['_rule'].get('min_mark', 1)
        max_mark = item['_rule'].get('max_mark', 101)
        try:
            mark = int(mark)
        except:
            mark = None

        if mark is not None and mark <= 100 and mark >= 1:
            if mark >= max_mark or mark < min_mark:
                continue

        elif min_mark != 1 or max_mark != 101:
            continue

        result.append(item)
    return result


def filter_operators(sections, op):
    '''
    filter operators
    '''
    specials = []
    commons = []
    for item in sections:
        if op in item['_rule']['operators']:
            specials.append(item)
        elif ALL_FLAG in item['_rule']['operators']:
            commons.append(item)
    return specials if len(specials) else commons


def paras_sort(sections, paras_dic):
    '''
    paras sort
    '''
    if not sections:
        return []
    for index, value in paras_dic.items():
        sections.sort(key=lambda x: x['_rule'][index], reverse=value)
        test_para = sections[0]['_rule'][index]
        results = []
        for section in sections:
            if section['_rule'][index] == test_para:
                results.append(section)
            else:
                break
        sections = results
    return sections


def filter_rule(sections, dicts, paras_dic=None):
    '''
    filter rule
    '''
    if 'operators' in dicts:
        sections = filter_operators(sections, dicts.pop('operators'))
    for index, section in enumerate(sections):
        section['_rate_'] = 0
        for key, value in dicts.items():
            alternative_rule = section["_rule"].get(key)
            include = alternative_rule.get('include') if alternative_rule else None
            exclude = alternative_rule.get('exclude') if alternative_rule else None
            if value not in exclude:
                if value in include:
                    section['_rate_'] += MATCH_WEIGHT
                    continue
                elif 'ofw' in include:
                    section['_rate_'] += ALL_WEIGHT
                    continue
            section['_rate_'] -= 1000
    sections.sort(key=lambda x: x['_rate_'], reverse=True)
    max_rate = sections[0]['_rate_']
    results = [s for s in sections if s.pop('_rate_') == max_rate]
    if paras_dic:
        sections = paras_sort(results, paras_dic)
    if len(sections) == 0:
        return []
    return sections[0]


def _convert_func(func):
    '''
    internal func
    '''
    def wrapper(*args, **kwargs):
        if func == bool:
            return bool(int(*args, **kwargs))
        return func(*args, **kwargs)
    return wrapper


def get_valid_params(query_dict, keys):
    '''
    get valid params by params rule
    '''
    try:
        result = {}
        for key in keys:
            paras = key.split('&')
            lenth = len(paras)
            if lenth > 0:
                tmp1 = paras[0]
                tmp = query_dict.get(tmp1)
                if lenth > 1:
                    tmp2 = paras[1]
                    if tmp2 == 'need' and not tmp:
                        raise ParamError(tmp1)
                    if tmp2 == 'notNeed' and not tmp:
                        continue
                    if lenth > 2 and tmp is None:
                        tmp = paras[2]
                    if lenth > 3 and tmp is not None:
                        try:
                            tmp = _convert_func(eval(paras[3]))(tmp)
                        except Exception, e:
                            _LOGGER.exception(e)
                            tmp = _convert_func(eval(paras[3]))(paras[2])
                            raise ParamError(tmp1)
                    result[tmp1] = tmp
        return result
    except Exception, e:
        _LOGGER.exception(e)
        if not isinstance(e, ParamError):
            raise InternalError('get param error')
        else:
            raise e


def get_smart_locale(svr_cc, svr_locale, cli_locale):
    '''
    get smart locale

    Parameters:
        svr_cc: country code specified by client ip
        svr_locale: locale specified by client ip
        cli_locale: locale transfered from client
    '''
    if not cli_locale:
        return [svr_locale]

    cli_args = cli_locale.split('_')
    if len(cli_args) != 2:
        return [svr_locale]

    cli_lang, cli_cc = cli_args[0], cli_args[1]
    if svr_cc is None or svr_locale is None or cli_cc == svr_cc:
        return [cli_locale]

    '''
    get smart locale by server side country code
    here we just use the svr_locale by REMOTE_IP,
    we can do more job here to specify the smart_locale later
    '''
    _LOGGER.warn('cli_locale[%s] not equal svr_locale[%s]'
                 % (cli_locale, svr_locale))
    '''
    here we define a new locale as candidate of smart_locale with svr_locale
    '''
    new_locale = '%s_%s' % (cli_lang, svr_cc)

    return [new_locale, svr_locale]
