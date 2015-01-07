# Copyright (c) 2011 Baina Info Inc. All rights reserved.
# author:kunli
# date:2011-11-19
# email:kunli@bainainfo.com
import re
import logging
from django.conf import settings
try:
    from django.contrib.gis.geoip import GeoIP
except Exception, e:
    from django.contrib.gis.utils import GeoIP

# FIXME: these info need persist in db and easy to update

_LOGGER = logging.getLogger('provision.service')

geoip = GeoIP(path='/usr/local/lib/python2.7/dist-packages/GeoLiteCity.dat')

_SUPPORT_LOCALE = ['zh_CN', 'en_US', 'ja_JP']
_RECOMMEND_LOCALE = {'zh': 'zh_CN', 'en': 'en_US', 'ja': 'ja_JP'}
_DEFAULT_LOCALE = settings.DEFAULT_LANGUAGE
_LOCALE_REG = re.compile(r'(\w+)[-_](\w+)')


def match_location(func):
    '''
    get Client conuntry by client ip, for smart locale
    '''

    def get_country(*args, **kwargs):
        request = args[0]
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        if ip != '0.0.0.0':
            try:
                content_dict = geoip.city(ip)
                if content_dict:
                    country_code = content_dict['country_code']
                    smart_locale = settings.LOCALE_MAP.get(country_code)
                    kwargs.update(
                        {'country': content_dict['country_code'],
                         'svr_locale': smart_locale})
                    _LOGGER.debug(
                        'found ccc[%s] locale[%s] for remote ip:%s'
                        % (country_code, smart_locale, ip))
                else:
                    _LOGGER.warn('not found GEO for remote ip:%s' % ip)
            except Exception, e:
                _LOGGER.error(e)

        return func(*args, **kwargs)
    return get_country


def auto_match_locale(func):
    """
    Auto select best match locale support by webzine if locale in query string
    """
    def auto_match(*args, **kwargs):
        request = args[0]
        locale = request.GET.get('l', None)
        if locale:
            query_dict = request.GET.copy()
            locale = locale.replace('-', '_')
            match = _LOCALE_REG.search(locale)
            if match:
                language = match.group(1)
                geo = match.group(2)
                standard_locale = '_'.join([language, geo.upper()])
                if standard_locale in _SUPPORT_LOCALE:
                    query_dict['l'] = standard_locale
                elif language in _RECOMMEND_LOCALE:
                    query_dict['l'] = _RECOMMEND_LOCALE[language]
                else:
                    query_dict['l'] = _DEFAULT_LOCALE
            request.GET = query_dict
        return func(*args, **kwargs)
    return auto_match
