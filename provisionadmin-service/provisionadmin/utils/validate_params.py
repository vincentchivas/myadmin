# -*- coding:utf-8 -*-
import logging
from provisionadmin.utils.exception import ParamsError, UnknownError


_LOGGER = logging.getLogger(__name__)
PARAM_OPTION_LIST = ["need", "noneed", "option"]


def _conv(func):
    '''
    internal func for converting data type
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
            paras = paras[:4]
            (param_key, param_option,
             param_type, default_value) = tuple(
                paras) + (None,) * (4 - len(paras))
            if not param_key or param_option not in PARAM_OPTION_LIST:
                # invalid config for parameter %key%
                continue
            param_value = query_dict.get(param_key)
            if param_value is None:
                if param_option == 'need':
                    raise ParamsError(param_key)
                if param_option == 'noneed':
                    continue
                if default_value is not None:
                    param_value = _conv(eval(param_type))(default_value)
                else:
                    param_value = default_value
            else:
                if param_type is not None:
                    try:
                        param_value = _conv(eval(param_type))(param_value)
                    except Exception as e:
                        raise ParamsError(param_key)
            result[param_key] = param_value
        return result
    except Exception as e:
        _LOGGER.exception(e)
        if not isinstance(e, ParamsError):
            raise UnknownError('get param error')
        else:
            _LOGGER.warn('check parameter exception![%s]' % e.msg)
            raise e
