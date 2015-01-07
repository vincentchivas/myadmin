# -*- coding: utf-8 -*-
"""
@author: zhhfang
@date: 2014-07-15
@description: define the exceptions
"""


class ParamsError(Exception):
    def __init__(self, msg):
        self.msg = 'Parameter error, %s' % msg


class AuthFailureError(Exception):
    def __init__(self, msg):
        self.msg = 'AuthFailure Error, %s' % msg


class UnknownError(Exception):
    def __init__(self, msg):
        self.msg = 'Unknown Error, %s' % msg


class UniqueCheckError(ValueError):
    def __init__(self, msg):
        self.msg = 'Value Error, %s' % msg


class DbError(Exception):
    def __init__(self, msg):
        self.msg = 'DbError, %s' % msg


class DataError(ValueError):
    def __init__(self, msg):
        self.msg = 'Data Error, %s' % msg
