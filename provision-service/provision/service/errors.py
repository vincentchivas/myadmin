import traceback
import logging

from django.http import (HttpResponse, HttpResponseNotFound,
                         HttpResponseBadRequest, HttpResponseServerError,
                         HttpResponseForbidden, HttpResponseNotModified)
from django.utils import simplejson
from django.conf import settings


_DEBUG = settings.DEBUG


_LOGGER = logging.getLogger('provision.service')

_ERROR_CODE_RESOURCE_NOT_EXISTS = 'ResourceNotExists'
_ERROR_CODE_RESOURCE_NOT_MODIFIED = 'ResourceNotModified'
_ERROR_CODE_PARAMETER_ERROR = 'MissingOrInvaildRequiredQueryParameter'
_ERROR_CODE_INTERNAL_SERVER_ERROR = 'InternalError'
_ERROR_CODE_AUTHORIZATION_FAILED = 'AuthError'

_ERROR_CODE = {
    _ERROR_CODE_AUTHORIZATION_FAILED: 'Authorization Failed.',
    _ERROR_CODE_RESOURCE_NOT_EXISTS: "The specified resource '%s' does not exist,args:%s.",
    _ERROR_CODE_RESOURCE_NOT_MODIFIED: "The specified resource '%s' is not modified,args:%s.",
    _ERROR_CODE_PARAMETER_ERROR: "A required query parameter '%s' was not specified for this request or was specified incorrectly.",
    _ERROR_CODE_INTERNAL_SERVER_ERROR: "The server encountered an internal error.Please retry the request."
}


class HttpResponseUnauthorized(HttpResponse):
    '''
    Derived from HttpRepsonse
    '''
    status_code = 401


def _write_error_response(response_class,
                          error_code,
                          error_message, log_error=None):
    '''
    Internal functin, write error response
    '''
    error = {
        'Code': error_code,
        'Message': error_message
    }
    if _DEBUG and log_error:
        error['Error'] = log_error
    return response_class(simplejson.dumps(error), mimetype='text/plain')


def _write_error_response2(response_class, error_message, log_error=None):
    '''
    Internal function
    '''
    _LOGGER.error(log_error)
    return response_class(error_message, content_type='application/json')


def authentication_fail(request, failed_info=None):
    '''
    authentication fail
    '''
    msg = _ERROR_CODE[_ERROR_CODE_AUTHORIZATION_FAILED]
    log_error = 'request:%s, %s' % (request.build_absolute_uri(), failed_info)
    _LOGGER.error(log_error)
    return _write_error_response(HttpResponseUnauthorized,
                                 _ERROR_CODE_AUTHORIZATION_FAILED,
                                 msg,
                                 log_error)


def resource_not_exist(request, resource, **karg):
    '''
    resource not exist
    '''
    format = _ERROR_CODE[_ERROR_CODE_RESOURCE_NOT_EXISTS]
    message = format % (resource, karg.__repr__())
    log_error = 'request:%s,%s' % (request.build_absolute_uri(), message)
    return _write_error_response(HttpResponseNotFound,
                                 _ERROR_CODE_RESOURCE_NOT_EXISTS,
                                 message,
                                 log_error=log_error)


def resource_not_modified(resource, **karg):
    '''
    resource not modified
    '''
    format = _ERROR_CODE[_ERROR_CODE_RESOURCE_NOT_MODIFIED]
    message = format % (resource, karg.__repr__())
    return _write_error_response(HttpResponseNotModified,
                                 _ERROR_CODE_RESOURCE_NOT_MODIFIED, message)


def bad_data(request):
    '''
    bad data
    '''
    error = {'result': 'Error', 'reason': 'Unrecognized data.'}
    message = simplejson.dumps(error)
    log_error = '%s -> Unrecognized data:\n%s' % (request.build_absolute_uri(),
                                                  request.raw_post_data)
    return _write_error_response2(HttpResponseBadRequest,
                                  message, log_error=log_error)


def blacklisted_request(source, name, value):
    '''
    blacklisted request
    '''
    error = {
        'result': 'Refused',
        'reason': 'One or more of the data item is blacklisted for the given source.',
        'source': source,
        'name': name,
        'value': value
    }
    message = simplejson.dumps(error)
    log_error = 'Blacklisted request: source=%s, name=%s, value=%s' % (
        source, name, value)
    return _write_error_response2(HttpResponseForbidden,
                                  message, log_error=log_error)


def exceeded_request(source, name, value, count):
    '''
    exceeded request
    '''
    error = {
        'result': 'Exceeded',
        'reason': 'One or more of the data item exceeds the limit for the given source.',
        'source': source,
        'name': name,
        'value': value,
        'count': count
    }
    message = simplejson.dumps(error)
    log_error = '_write_error_response2 request: source=%s, name=%s, value=%s, count=%s' % (
        source, name, value, count)
    return _write_error_response2(HttpResponseForbidden,
                                  message,
                                  log_error=log_error)


def parameter_error(request, parameter):
    '''
    return parameter error
    '''
    format = _ERROR_CODE[_ERROR_CODE_PARAMETER_ERROR]
    message = format % parameter
    log_error = 'request:%s,%s' % (request.build_absolute_uri(), message)
    _LOGGER.warn(log_error)
    return _write_error_response(HttpResponseBadRequest,
                                 _ERROR_CODE_PARAMETER_ERROR,
                                 message,
                                 log_error=log_error)


TEMPLATE_SERVER_ERROR_GET = '%(method)s : %(uri)s, Internal Server Error Info: %(message)s\n%(trace_stack)s'
TEMPLATE_SERVER_ERROR_POST = '%(method)s : %(uri)s, Body = %(body)s, Internal Server Error Info: %(message)s\n%(trace_stack)s'


def internal_server_error(request, error_message=None, exc_info=None):
    '''
    return internal server error
    '''
    message = _ERROR_CODE[_ERROR_CODE_INTERNAL_SERVER_ERROR]
    trace_stack = '\n'.join(traceback.format_exception(*exc_info))
    vars = {
        'method': request.method,
        'body': request.raw_post_data,
        'message': error_message,
        'uri': request.build_absolute_uri(),
        'trace_stack': trace_stack
    }
    template = TEMPLATE_SERVER_ERROR_POST\
        if request.method == 'POST' else TEMPLATE_SERVER_ERROR_GET
    log_error = template % vars
    _LOGGER.error(log_error)
    return _write_error_response(HttpResponseServerError,
                                 _ERROR_CODE_INTERNAL_SERVER_ERROR,
                                 message,
                                 log_error=log_error)


def empty_array_response(request):
    '''
    response empty
    '''
    _LOGGER.warn('request:%s,empty array response' %
                 request.build_absolute_uri())
    return HttpResponse('[]', mimetype='text/plain')
