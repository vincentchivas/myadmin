from provisionadmin.settings import STATIC_ROOT 


def upload_apk(apk_file):
    fp = open(STATIC_ROOT+'/dolphin.apk', 'w')
    fp.write(apk_file)


def download_apk():
    fp = open(STATIC_ROOT+'/dolphin.apk', 'r')
    data = fp.read()
    return data


def build_apk():
    pass
