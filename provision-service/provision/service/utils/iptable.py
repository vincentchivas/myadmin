#!/usr/bin/env python
# -*- coding:utf-8 -*-
# Copyright (c) 2012 Baina Info Inc. All rights reserved.
# Created On Jan 25, 2013
# @Author : Jun Wang
# Email: jwang@bainainfo.com
import urllib2
import logging
import time
from django.utils import simplejson
from provision.utils import ip2int
from provision.service.models import iptabledb


logger = logging.getLogger('provision.service')

VALID_TIME = 7 * 86400

_IP_LOOKUP_API_FORMAT = "http://int.dpool.sina.com.cn/iplookup/iplookup.php?format=json&ip=%s"


def _request_url(url):
    '''
    internal request to url
    '''
    response = urllib2.urlopen(url)
    return response.read()


def get_ip_info(ip):
    url = _IP_LOOKUP_API_FORMAT % ip
    dic = None
    try:
        ip_int = ip2int(ip)
        dic = iptabledb.get_info_by_ip(ip_int, VALID_TIME)
        if dic:
            return dic
        else:
            content = _request_url(url)
            if isinstance(content, str):
                dic = simplejson.loads(content)
                if isinstance(dic, dict):
                    if 'start' in dic and 'end' in dic:
                        dic['start_int'] = ip2int(dic['start'])
                        dic['end_int'] = ip2int(dic['end'])
                        dic['timestamp'] = int(time.time())
                        iptabledb.save_ip(dic)
    except urllib2.URLError, e:
        logger.warn("Failed to get city name with url %s. Error:%s" % (url, e))
        return None
    return dic
