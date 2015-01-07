from uuid import UUID
from django.core.serializers.json import DateTimeAwareJSONEncoder
from django.db import models
from django.utils.functional import Promise
from django.utils.encoding import force_unicode
from django.utils import simplejson
from django.http import HttpResponse
from decimal import Decimal
from provision.settings import DEBUG
from provision.utils.respcode import OK


def json_encode(data):

    def _any(data):
        ret = None
        if isinstance(data, (list, tuple)):
            ret = _list(data)
        elif isinstance(data, UUID):
            ret = str(data)
        elif isinstance(data, dict):
            ret = _dict(data)
        elif isinstance(data, Decimal):
            # json.dumps() can't handle Decimal
            ret = str(data)
        elif isinstance(data, models.query.QuerySet):
            # Actually its the same as a list ...
            ret = _list(data)
        elif isinstance(data, models.Model):
            ret = _model(data)
        # here we need to encode the string as unicode (otherwise we get utf-16 in the json-response)
        elif isinstance(data, str):
            ret = unicode(data, 'utf-8')
        # see http://code.djangoproject.com/ticket/5868
        elif isinstance(data, Promise):
            ret = force_unicode(data)
        else:
            ret = data
        return ret

    def _model(data):
        ret = {}
        # If we only have a model, we only want to encode the fields.
        for f in data._meta.fields:
            ret[f.attname] = _any(getattr(data, f.attname))
        return ret

    def _list(data):
        ret = []
        for v in data:
            ret.append(_any(v))
        return ret

    def _dict(data):
        ret = {}
        for k, v in data.items():
            ret[k] = _any(v)
        return ret

    ret = _any(data)

    return simplejson.dumps(ret, cls = DateTimeAwareJSONEncoder, ensure_ascii = False, indent = 4 if DEBUG else 0)


def _json_response(status, data):
    d = {'status':status, 'data':data}
    return HttpResponse(json_encode(d), content_type = 'application/json; charset=utf-8')


def json_response_ok(data = None):
    return _json_response(OK, data)


def json_response_error(error_code, msg = None):
    return _json_response(error_code, msg)


def json_request(request):
    return simplejson.loads(request.raw_post_data)


