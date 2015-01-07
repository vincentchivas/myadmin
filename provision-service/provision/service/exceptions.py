class ServerError(Exception):
    '''
    Server Error Exception Class
    '''

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Server Error:' + repr(self.msg)


class ClientError(Exception):
    '''
    Client Error Exception Class
    '''

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return 'Client Error:' + repr(self.msg)


class InternalError(ServerError):
    '''
    Internal Error Exception Class
    '''

    def __init__(self, msg):
        self.msg = 'Internal error, ' + msg


class ParamError(ClientError):
    '''
    ParamError Exception Class
    '''

    def __init__(self, msg):
        self.msg = 'Parameter error, ' + msg
