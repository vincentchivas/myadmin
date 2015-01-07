# -*- coding: UTF-8 -*-
# from util_log import logger
import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
# from email.mime.image import MIMEImage
import threading
# import settings

LOG_FILE = '/var/app/log/provisionadmin-service/mail.log'
handler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1024 * 1024)
fmt = '%(asctime)s-%(filename)s-%(lineno)s-%(name)s-%(levelname)s-%(message)s'
formatter = logging.Formatter(fmt)
handler.setFormatter(formatter)

_LOGGER = logging.getLogger('mail')
_LOGGER.addHandler(handler)
_LOGGER.setLevel(logging.DEBUG)

MAIL_SERVER = "mail.bainainfo.com:587"
MAIL_USER = "i18nStudio@baina.com"
MAIL_PASSWORD = "i18P@55word"
MAIL_FROM = "I18N Studio<i18nStudio@bainainfo.com>"


def _prepare_smtp():
    smtp = smtplib.SMTP(MAIL_SERVER)
    smtp.starttls()
    smtp.login(MAIL_USER, MAIL_PASSWORD)
    return smtp


def _prepare_msg(subject, body, mail_to, mail_cc, is_picture, att_path):
    msg = MIMEMultipart()
    msg["From"] = MAIL_FROM
    msg["TO"] = ";".join(mail_to)
    msg["CC"] = ";".join(mail_cc)
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html", "utf-8"))
    if is_picture:
        # _add_image(msg)
        _LOGGER.info("add picture")
    if att_path:
        _add_attach(msg, att_path)
    return msg


def _add_attach(msg, filepath):
    if not os.path.exists(filepath):
        return None
    else:
        filename = filepath.split('/')[-1]
        att = MIMEText(open(filepath).read(), 'base64', 'utf-8')
        att['Content-Type'] = 'application/octet-stream'
        att['Content-Disposition'] = 'attachment; filename=%s' % filename
        msg.attach(att)


'''
def _add_image(msg):
    for poll_item in setting.POLL_LIST:
        project_name = poll_item.get("name")

        root_path = "/tmp/"
        path = root_path + project_name + ".png"
        try:
            fp = open(path, 'rb')
            msgImgage = MIMEImage(fp.read())
            fp.close()
            msgImgage.add_header('Content-ID', '<image_%s>' % project_name)
            msgImgage[
                "Content-Disposition"] = 'attachment;filename = %s.png'
                % project_name
            msg.attach(msgImgage)
        except IOError:
            print 'IOError'
            #logger.error("File %s not exits" % path)
        except Exception, e:
            print 'e'
            #logger.error("exception accured in add image![%s]" % e)
 '''


def _send_email(subject, body, mail_to, mail_cc, is_picture=False,
                att_path=None):
    try:
        to_list = mail_to + mail_cc
        msg = _prepare_msg(subject, body, mail_to, mail_cc,
                           is_picture=is_picture, att_path=att_path)
        smtp = _prepare_smtp()
        smtp.sendmail(MAIL_FROM, to_list, msg.as_string())
        smtp.quit()
    except Exception, exception:
        _LOGGER.info("exception accurred in send email![%s]" % str(exception))


class EmailThread(threading.Thread):

    def __init__(self, subject, body, mail_to, mail_cc, is_picture=False,
                 att_path=None):
        self.subject = subject
        self.body = body
        self.mail_to = mail_to
        self.mail_cc = mail_cc
        self.is_picture = is_picture
        self.att_path = att_path
        threading.Thread.__init__(self)

    def run(self):
        _send_email(self.subject, self.body, self.mail_to,
                    self.mail_cc, att_path=self.att_path)


def send_message(subject, template, mail_to, mail_cc, is_picture=False,
                 att_path=None, *args):
    '''
    subject: mail subject
    template: mail content template, in this function we use html
    mail_to: the user list we mail_to
    mail_cc: 抄送
    is_picture:是否还有图片
    att_path: 附件地址，默认为空
    *args 可变参数，根据模板中需要的可变参数，传入相应的值

    eg:当创建任务的时候调用
    send_message('create task','../template/create_task.html',
    [bhuang@bainainfo.com],[yqyu@bainainfo],False,None,'a','b','c')
    'a','b','c'会映射到相应的占位符
    '''
    _LOGGER.info("mail_to:%s and mail_cc:%s" % (mail_to, mail_cc))
    try:
        f = open(template, 'r')
        s = f.read()
        format_s = s % args
    except Exception, exception:
        _LOGGER.info(
            "read file and format occurred exception:%s" % str(exception))
    email_thread = EmailThread(
        subject, format_s, mail_to, mail_cc, is_picture, att_path)
    try:
        email_thread.start()
    except Exception, exception:
        _LOGGER.info("send mail occurred:%s" % str(exception))
