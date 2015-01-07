'''
Created on Aug 22, 2011

@author: chzhong
'''
import pyDes
import base64

_des = None
_DOLPHIN_KEY = base64.b64decode('//pnjQYeN4A=')


def _ensure_des():
    global _des
    if _des is None:
        _des = pyDes.des(_DOLPHIN_KEY, pyDes.ECB, padmode=pyDes.PAD_PKCS5)
    return _des


def get_des():
    return _ensure_des()


def encrypt(data):
    if isinstance(data, unicode):
        data = data.encode('utf-8')
    des = _ensure_des()
    return des.encrypt(data)


def decrypt(data):
    des = _ensure_des()
    return des.decrypt(data)


def encrypt_as_base64(data, urlsafe=False):
    encrypted = encrypt(data)
    return base64.urlsafe_b64encode(encrypted) if urlsafe else base64.b64encode(encrypted)


def decrypt_base64(data, urlsafe=False):
    encrypted = base64.urlsafe_b64decode(
        data) if urlsafe else base64.b64decode(data)
    return decrypt(encrypted)
