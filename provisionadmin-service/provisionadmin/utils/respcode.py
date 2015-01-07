# -*- coding: utf-8 -*-
"""
@author: zhhfang
@date: 2014-07-15
@description: The response code of API
"""

OK = 0

UNKNOWN_ERROR = 1
HTTPS_REQUIRED = 2
PARAM_REQUIRED = 3
DATA_ERROR = 4
DB_ERROR = 5
PERMISSION_DENY = 6
AUTH_ERROR = 7
PASSWORD_UNMATCH = 8
SAVE_ERROR = 9
PARAM_ERROR = 10
METHOD_ERROR = 11
IO_ERROR = 12
CONTENT_NOT_FOUND = 13
# for preset admin
DUPLICATE_DELETE = 1001  # when delete one data twice or more
ONLINE_DATA_UNDELETE = 1002  # data must be deleted from online first
DATA_NOT_UPLOAD_TO_PRE = 1003  # data must be upload to pre-env first,then ec2
DATA_RELETED_BY_OTHER = 1004  # data releted by other data when delete
DATA_DELETE_COMFIRM = 1005  # data delete  need comfirm
