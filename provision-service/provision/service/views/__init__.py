import httplib
import json

from django.utils import simplejson
from django.http import HttpResponse, HttpResponseNotFound, \
    HttpResponseServerError


DEFAULT_SOURCE = 'ofw'
ALL_FLAG = 'all_condition'
OTHER = 'other_condition'
OPERATORS = ['00', '01', '02', '03']
ALL_WEIGHT = 1
MATCH_WEIGHT = 100


def json_response(func):
    '''
    json response wrapper
    '''
    def json_responsed(request, *args, **kwargs):
        status_code = httplib.OK
        retval = func(request, *args, **kwargs)
        content = json.dumps(retval, skipkeys=True, ensure_ascii=False)
        response = HttpResponse(
            content,
            content_type='application/json; charset=utf-8',
            status=status_code)
        response['Access-Control-Allow-Origin'] = "*"
        return response
    return json_responsed


def response_json(obj):
    '''
    format data to json
    '''
    content = simplejson.dumps(obj, ensure_ascii=False)
    response = HttpResponse(
        content, content_type='application/json; charset=utf-8')
    response['Access-Control-Allow-Origin'] = "*"
    return response


def error404(request):
    '''
    return 404 http response
    '''
    return HttpResponseNotFound(""""
Sorry, we can't find what you want...
""")


def error500(request):
    '''
    return 500 http response
    '''
    return HttpResponseServerError("""
Sorry, we've encounter an error on the server.<br/>
Please leave a feedback <a href="/feedback.htm">here</a>.
""", content_type="text/html; charset=utf-8")
