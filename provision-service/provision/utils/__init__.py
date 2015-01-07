import datetime
import calendar
import struct
import os
import socket
import fcntl
import time
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

ONE_DAY = datetime.timedelta(days=1)

perf_logger = logging.getLogger('provision.perf')


def date_part(date):
    '''
    Return the date part of a given day.
    '''
    if date:
        return date.replace(hour=0, minute=0, second=0, microsecond=0)
    return None


def now():
    '''
    Return now.
    '''
    return datetime.datetime.now()


def today():
    '''
    Return the date part of today.
    '''
    return date_part(datetime.datetime.now())


def tomorrow():
    '''
    Return the date part of tomorrow.
    '''
    return today() + ONE_DAY


def yesterday():
    '''
    Return the date part of yesterday.
    '''
    return today() - ONE_DAY


def lastmonth():
    '''
    Return the date list of last 30 days.
    '''
    days = []
    # for i in range(30):
    for i in range(1, 30):
        pre = datetime.timedelta(days=i)
        days.append(today() - pre)
    return days


def dotted_quad_to_num(ip):
    "convert decimal dotted quad string to long integer"

    hexn = ''.join(["%02X" % long(i) for i in ip.split('.')])
    return long(hexn, 16)


def filter_fields(data_dict, key_dict):
    option = [0, 1]
    result_dict = {}
    for v in key_dict.values():
        if v not in option:
            raise ValueError('field dict value should be 1 or 0.')
    if sum(key_dict.values()) == 0:
        for key in data_dict:
            if key in key_dict:
                data_dict.pop(key)
        result_dict = data_dict
    else:
        for key in key_dict:
            if key in data_dict and key_dict[key]:
                result_dict[key] = data_dict[key]
    return result_dict


def datetime2timestamp(dt):
    '''
    Converts a datetime object to UNIX timestamp in milliseconds.
    '''
    if hasattr(dt, 'utctimetuple'):
        t = calendar.timegm(dt.utctimetuple())
        timestamp = int(t) + dt.microsecond / 1000000
        return timestamp * 1000
    return dt


def timestamp2datetime(timestamp):
    '''
    Converts UNIX timestamp in milliseconds to a datetime object.
    '''
    if isinstance(timestamp, (int, long, float)):
        return datetime.datetime.utcfromtimestamp(timestamp / 1000)
    return timestamp


def get_bool(value):
    if (isinstance(value, bool) and value) or (isinstance(value, str) and value.lower() == 'true'):
        return True
    else:
        return False


def ip2int(addr):
    return struct.unpack("!I", socket.inet_aton(addr))[0]


def int2ip(addr):
    return socket.inet_ntoa(struct.pack("!I", addr))


def perf_logging(func):
    """
    Record the performance of each method call.
    Also catches unhandled exceptions in method call and response a 500 error.
    """
    def pref_logged(*args, **kwargs):
        argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
        fname = func.func_name
        req = args[0]
        msg = '%s %s -> %s(%s)' % (req.method, req.META['PATH_INFO'], fname, ','.join('%s=%s' %
                                                                                      entry for entry in zip(argnames[1:], args[1:]) + kwargs.items() + req.GET.items()))
        startTime = time.time()
        perf_logger.info('%s -> Start time: %d.' % (msg, 1000 * startTime))
        retVal = func(*args, **kwargs)
        perf_logger.info('%s -> End Start time: %d.' % (msg, 1000 * startTime))
        endTime = time.time()
        perf_logger.info('%s -> %s ms.' % (msg, 1000 * (endTime - startTime)))
        return retVal
    return pref_logged


def sendmail(receivers, message):
    print 'start send mail!'
    sender = 'conch.monitor@gmail.com'
    password = 'bainaP@55word'
    #text = 'pm2.5 api can not work, please check'
    msgRoot = MIMEMultipart('related')
    msgRoot['Subject'] = 'API_BreakDown%s' % (
        datetime.date.today() - datetime.timedelta(days=1))
    msgText = MIMEText(message, 'html', 'utf-8')
    msgRoot.attach(msgText)
    smtp = smtplib.SMTP()
    smtp.connect('smtp.gmail.com:587')
    smtp.starttls()
    smtp.login(sender, password)
    for receiver in receivers:
        smtp.sendmail(sender, receivers, msgRoot.as_string())
    smtp.quit()


def report(message):
    email_list = ('yfhe@bainainfo.com', )
    sendmail(email_list, message)


def get_ip_address():
    f = os.popen("ifconfig -s|grep -v Iface|awk '{print $1}'")
    interface = f.readlines()
    f.close()
    ip_list = []
    for ifname in interface:
        ifname = ifname.strip()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ipaddr = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', ifname[:15])
        )[20:24])
        ip_list.append(ipaddr)
    return ip_list
