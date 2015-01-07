# -*- coding: utf-8 -*-
"""
@author: yqyu
@date: 2014-07-15
@description: create a QRcode
"""

import qrcode


def make_qr(url, path):
    """
    Create a QRcode
    Parameters:
        -url: The url for Need to create a QRcode,
        -path: Qr code storage path
    Return:
        -1. None
    """
    new_qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    new_qr.add_data(url)
    new_qr.make(fit=True)
    img = new_qr.make_image()
    img.save(path)
