#-*- coding:utf-8 -*-
import MySQLdb
import simplejson
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MySql_Conn(object):

    @classmethod
    def new(cls, host, user, passwd, dbname, port):
        # create mysql connection instance
        instance = cls()
        instance._host = host
        instance._user = user
        instance._passwd = passwd
        instance._port = port
        instance._dbname = dbname
        instance.__connect()

        return instance

    def __connect(self):
        try:
            self._conn = MySQLdb.connect(
                host=self._host, user=self._user, passwd=self._passwd, port=self._port)
            if not self._conn:
                logger.error("MySQL connecting failed!")
            else:
                logger.info("MySQL connecting succ.")
                self.execute_sql('set autocommit=0')
        except MySQLdb.Error, e:
            logger.error("MySQL error %d: %s" % (e.args[0], e.args[1]))
            self._conn = None

    def __disconnect(self):
        if self._conn:
            cur = self._conn.cursor()
            cur.close()
            self._conn.close()
            self._conn = None

    def __reset_connect(self):
        self.__disconnect()
        self.__connect()

    def execute_sql(self, sql_str):
        if self._conn:
            try_count = 0
            while try_count < 3:
                try:
                    cur = self._conn.cursor()
                    self._conn.select_db(self._dbname)
                    cur.execute(sql_str)
                    self._conn.commit()
                    break
                except MySQLdb.Error, e:
                    try_count += 1
                    self.__reset_connect()
                    logger.error("MySQL error! %s: %s, try count:%s sql_str: %s" % (e.args[0], e.args[1], try_count, sql_str))

    def query_sql(self, sql_str):
        if self._conn:
            try_count = 0
            while try_count < 3:
                try:
                    cur = self._conn.cursor()
                    self._conn.select_db(self._dbname)
                    count = cur.execute(sql_str)
                    logger.info("MySQL query %s rows record" % count)
                    results = cur.fetchall()
                    self._conn.commit()

                    return results
                except MySQLdb.Error, e:
                    try_count += 1
                    self.__reset_connect()
                    logger.error("MySQL error! %s, try count:%s" % (e, try_count))

        return None
