import logging
from provisionadmin.db.config import ID_DB


_LOGGER = logging.getLogger(__name__)

ID_INIT = 00L

IDS = ('user', 'preset', 'module')


def get_next_id(id_name):
    if id_name not in IDS:
        _LOGGER.error('id type error:%s' % id_name)

    result = ID_DB.seq_id.find_and_modify(
        {'_id': id_name}, {'$inc': {'seq': 1L}}, upsert=True, new=True)
    return result['seq']
