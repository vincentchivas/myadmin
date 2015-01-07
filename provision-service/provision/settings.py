# Django settings for webb project.
import os
import sys
from ConfigParser import ConfigParser
from django.utils.dictconfig import dictConfig
from db import parse_conn_string

# sys.path.insert(0,'/home/mobotk/workspace/dolphin_operation/DolphinOperation/ops/dolphinop-service/')

# sys.path.insert(0,'/home/mobotk/workspace/dolphin_operation/DolphinOperation/ops/dolphinop-service/')

DEBUG = True
COMPRESS_ENABLED = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
}
import django
if django.get_version()[2] == '4':
    DATABASES = {
        'default': {}
    }

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'zh-cn'

SITE_ID = 1

DEFAULT_CHARSET = 'utf-8'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

STATICFILES_DIRS = (
)
# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'compressor.finders.CompressorFinder',
)


# Make this unique, and don't share it with anybody.
SECRET_KEY = 'ik-%+qsuieygf!l0t^4!u__l%+=n(#+x59q-w)58g=1-v)#r_!'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    #'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    #'django.middleware.csrf.CsrfResponseMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    'provision.service.middleware.SetRemoteAddrMiddleware',
)

#SESSION_ENGINE = 'django.contrib.sessions.backends.file'
#SESSION_SAVE_EVERY_REQUEST = True

ROOT_URLCONF = 'provision.urls'


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))


TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(SITE_ROOT, 'templates'),
    os.path.join(SITE_ROOT, 'web/templates'),
)

INSTALLED_APPS = (
    #'django.contrib.auth',
    #'django.contrib.contenttypes',
    #'django.contrib.sessions',
    #'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'provision.service',
    'compressor',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'detail': {
            'format': '%(asctime)s %(levelname)s %(name)s [%(filename)s:%(lineno)d] %(funcName)s %(message)s'
        },
        'message_only': {
            'format': '%(asctime)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(asctime)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'django.utils.log.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'detail',
            'filename': '/tmp/provision.log',
            'when': 'D',
            'backupCount': 7
        },
        'perf': {
            'level': 'INFO',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'message_only',
            'filename': '/tmp/provision.log',
            'when': 'D',
            'backupCount': 7
        },
        'db': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'message_only',
            'filename': '/tmp/provision.log',
            'when': 'D',
            'backupCount': 7
        },
        'err': {
            'level': 'ERROR',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'formatter': 'detail',
            'filename': '/tmp/provision_service.err',
            'when': 'D',
            'backupCount': 7
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'provision.service.views': {
            'handlers': ['file', 'err'],
            'level': 'DEBUG',
        },
        'provision.db': {
            'handlers': ['db', 'err'],
            'level': 'DEBUG',
        },
        'provision.service': {
            'handlers': ['file', 'err'],
            'level': 'DEBUG',
        },
    }
}

DATA_DIR = '/tmp'

DOLPHINOP_DB = None
DB_CONN = None

REQUEST_TIME_OUT = 1.0
MAX_RETRY_COUNT = 3
HTTP_MAX_AGE = 60 * 60 * 24  # 1 day

MAX_IP_COUNT_PER_DAY = 1000
MAX_SIM_COUNT = 400

DEFAULT_LANGUAGE = None
DEFAULT_SOURCE = 'ofw'

CLIENT_ARGS = {
    'os': ['android', 'aPad', 'iPhone', 'iPhone_jb', 'iPad', 'wphone', 'wSlate'],
    'source': [],
}

STATIC_URL = 'http://opscn.dolphin-browser.com/static/'
STATIC_RELATIVE_URL = '/static/'

SECTION = 'provision-service'
DOMAIN = None
SERVER = None

LOCALE_MAP = {}

def _load_config():
    global DEBUG, STATIC_URL, MAX_IP_COUNT_PER_DAY, MAX_SIM_COUNT, DATA_DIR, TEMPLATE_DEBUG, DOLPHINOP_DB, REQUEST_TIME_OUT, MAX_RETRY_COUNT, HTTP_MAX_AGE, DEFAULT_LANGUAGE, COMPRESS_ENABLED, DOMAIN, SERVER, DB_CONN
    cp = ConfigParser()
    cp.read(["/var/app/enabled/provision-service/provision-service.cfg"])
    DEBUG = cp.getboolean(SECTION, 'debug')
    COMPRESS_ENABLED = cp.getboolean(SECTION, 'compress')
    DOMAIN = cp.get(SECTION, 'domain')
    SERVER = cp.get(SECTION, 'server')
    TEMPLATE_DEBUG = DEBUG
    DB_CONN = cp.get(SECTION, 'mongodb_conf')
    DOLPHINOP_DB = parse_conn_string(cp.get(SECTION, 'dolphinop_db'))
    DB_CONN = cp.get(SECTION, 'mongodb_conf')
    logs_dir = cp.get(SECTION, 'logs_dir')
    DATA_DIR = cp.get(SECTION, 'data_dir')
    MAX_IP_COUNT_PER_DAY = cp.getint(SECTION, 'max_ip_count')
    MAX_SIM_COUNT = cp.getint(SECTION, 'max_sim_count')
    REQUEST_TIME_OUT = cp.getfloat(SECTION, 'request_timeout')
    MAX_RETRY_COUNT = cp.getint(SECTION, 'max_retry')
    HTTP_MAX_AGE = cp.getint(SECTION, 'http_max_age')
    DEFAULT_LANGUAGE = cp.get(SECTION, 'default_language')
    STATIC_URL = 'http://%s/static/' % cp.get(SECTION, 'domain')
    LOGGING['handlers']['file']['filename'] = os.path.join(
        logs_dir, 'provision.log')
    LOGGING['handlers']['err'][
        'filename'] = os.path.join(logs_dir, 'error.log')
    LOGGING['handlers']['perf'][
        'filename'] = os.path.join(logs_dir, 'perf.log')
    LOGGING['handlers']['db']['filename'] = os.path.join(logs_dir, 'db.log')
    if DEBUG is False:
        LOGGING['handlers']['file']['level'] = 'INFO'
    dictConfig(LOGGING)

    #load country_code--locale map tab
    locale_map_fp = open('/usr/local/lib/python2.7/dist-packages/localemap.tab', 'r')
    for item in locale_map_fp:
        item = item.replace('\n','')
        cc, locale = item.split('\t')
        LOCALE_MAP[cc] = locale

_load_config()
