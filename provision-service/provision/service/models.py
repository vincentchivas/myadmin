from django.conf import settings
from provision.db import config, sharedb, desktopdb, presetdb

DB = settings.DOLPHINOP_DB

config(presetdb, **DB)
config(desktopdb, **DB)
config(sharedb, **DB)
