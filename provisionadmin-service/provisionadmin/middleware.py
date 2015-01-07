import time, logging
from django.conf import settings
from django.utils.encoding import smart_unicode
# from provisionadmin.utils.common import flatten_dict


_LOGGER = logging.getLogger('provisionadmin')


class LogMiddleware:

    start = None

    def process_request(self, request):
        self.start = time.time()

    def process_response(self, request, response):
        if not self.start:
            return response

        try:
            path = smart_unicode(request.path)
            proctime = round(time.time() - self.start, 3)
            #get = flatten_dict(request.GET)
            #post = flatten_dict(request.POST)

            Origin_header = request.META.get('HTTP_ORIGIN')
            ip = request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR')
            status_code = response.status_code

            _LOGGER.info(u'%u %s exec_time=%.3fs IP=%s RESP=%s time between %s and %s' %
                    (status_code, path, proctime, ip, '', self.start, time.time()))

        except Exception, e:
            _LOGGER.exception(e)

        accept_header = request.META.get('HTTP_ACCESS_CONTROL_REQUEST_HEADERS')
        if accept_header:
            response['Access-Control-Allow-Headers'] = accept_header
        response['Access-Control-Allow-Origin'] = Origin_header
        response['Access-Control-Allow-Credentials'] = 'true'

        return response

