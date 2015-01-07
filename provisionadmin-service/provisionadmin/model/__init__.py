import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

_LOGGER = logging.getLogger("model")

CONNECT_STRINGS = {
    "dol_op_admin": "mysql://root:123456@172.16.7.101:3306/dolphinopadmin"}

SESSION_DICT = {}

for key in CONNECT_STRINGS:
    conn_string = CONNECT_STRINGS[key]
    try:
        engine = create_engine(conn_string)
        SESSION_DICT[key] = sessionmaker(bind=engine)
    except:
        _LOGGER.error("connet %s failed" % key)
