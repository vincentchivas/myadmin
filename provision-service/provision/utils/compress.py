'''
Created on Aug 22, 2011

@author: chzhong
'''
import os
import zipfile
import tarfile


def zip_compress(filename):
    prefix, _ = os.path.splitext(filename)
    zip_path = prefix + '.zip'
    if not os.path.exists(zip_path):
        archive = zipfile.ZipFile(
            zip_path, mode='w', compression=zipfile.ZIP_DEFLATED)
        archive.write(filename, arcname=os.path.basename(filename))
        archive.close()
    with open(zip_path, 'rb') as fp:
        return fp.read()


def tar_gz_compress(filename):
    prefix, _ = os.path.splitext(filename)
    zip_path = prefix + '.tar.gz'
    if not os.path.exists(zip_path):
        archive = tarfile.open(zip_path, mode='w:gz')
        archive.add(filename, arcname=os.path.basename(filename))
        archive.close()
    with open(zip_path, 'rb') as fp:
        return fp.read()


def tar_compress(filename):
    prefix, _ = os.path.splitext(filename)
    zip_path = prefix + '.tar'
    if not os.path.exists(zip_path):
        archive = tarfile.open(zip_path, mode='w')
        archive.add(filename, arcname=os.path.basename(filename))
        archive.close()
    with open(zip_path, 'rb') as fp:
        return fp.read()
