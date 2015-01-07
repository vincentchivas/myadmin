'''
Created on Jun 20, 2011

@author: chzhong
'''
from django.http import HttpResponseRedirect
import urllib2
_TIME_OUT = 5


class SetRemoteAddrMiddleware(object):

    def process_request(self, request):
        if 'HTTP_X_REAL_IP' in request.META:
            try:
                request.META['REMOTE_ADDR'] = request.META['HTTP_X_REAL_IP']
            except:
                # This will place a valid IP in REMOTE_ADDR but this shouldn't
                # happen
                request.META['REMOTE_ADDR'] = '0.0.0.0'


class SetRemoteCountryMiddleware(object):

    def process_request(self, request):
        if request.path.find('/pages/hotapps/index.html') == -1:
            return
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        if ip == '0.0.0.0':
            return
        sent_url = 'http://www.telize.com/geoip/%s?callback=getgeoip' % (ip)
        try:
            content = urllib2.urlopen(sent_url, timeout=_TIME_OUT).read()
            content_filter = str(content[9:-3])
            content_dic = eval(content_filter)
            if content_dic['country_code3'] == 'USA' or content_dic['country'] == 'United States':
                return HttpResponseRedirect('https://dolphin.studio.quixey.com/promoted?ref=dolphinhome')
        except:
            return
