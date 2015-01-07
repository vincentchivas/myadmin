#! /usr/bin/env python
# coding: utf-8
import types
import re


class MetaValidate(object):
    @classmethod
    def check_validate(cls, shape, value):
        handle = None
        methodName = "Is" + shape
        handle = getattr(cls, methodName)
        return handle(value)

    @classmethod
    def IsNumber(cls, varObj):
        return isinstance(varObj, types.IntType)

    @classmethod
    def IsString(cls, varObj):
        return isinstance(varObj, types.StringType)

    @classmethod
    def IsFloat(cls, varObj):
        return isinstance(varObj, types.FloatType)

    @classmethod
    def IsDict(cls, varObj):
        return isinstance(varObj, types.DictType)

    @classmethod
    def IsTuple(cls, varObj):
        return isinstance(varObj, types.TupleType)

    @classmethod
    def IsList(cls, varObj):
        return isinstance(varObj, types.ListType)

    @classmethod
    def IsBoolean(cls, varObj):
        return isinstance(varObj, types.BooleanType)

    @classmethod
    def IsEmpty(cls, varObj):
        if len(varObj) == 0:
            return True
        return False

    @classmethod
    def IsNone(cls, varObj):
        return isinstance(varObj, types.NoneType)

    @classmethod
    def IsEmail(cls, varObj):
        # 判断是否为邮件地址
        rule = '[\w-]+(\.[\w-]+)*@[\w-]+(\.[\w-]+)+$'
        match = re.match(rule, varObj)
        if match:
            return True
        return False

    @classmethod
    def IsChineseChar(cls, varObj):
        # 判断是否为中文字符
        if varObj[0] > chr(127):
            return True
        return False

    @classmethod
    def IsLegalAccounts(cls, varObj):
        # 判断帐号是否合法 字母开头，允许4-16字节，允许字母数字下划线
        rule = '[a-zA-Z][a-zA-Z0-9_]{3,15}$'
        match = re.match(rule, varObj)
        if match:
            return True
        return False

    @classmethod
    def IsIpAddr(cls, varObj):
        # 匹配IP地址
        rule = '\d+\.\d+\.\d+\.\d+'
        match = re.match(rule, varObj)
        if match:
            return True
        return False
