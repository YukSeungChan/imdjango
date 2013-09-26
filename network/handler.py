# -*- coding:utf8 -*-
import bson, logging, threading
from urlparse import urlparse, parse_qs
from twisted.internet import reactor, protocol

from django.conf import settings
from django.core import urlresolvers

from imdjango.exceptions import IMError, NoParameterError, BadRequestError, InvalidParameterError

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('imdjango')

class IMRequestHandler(protocol.Protocol):
    
    def connectionMade(self):
        logger.info("connectionMade - %s:%s"%(self.transport.client[0],self.transport.client[1]))
        self.factory.handlers.append(self)
        
    def dataReceived(self, data):
        logger.info("dataReceived - %s:%s - %s"%(self.transport.client[0],self.transport.client[1],data))
        try:
            self.handle(data)
        except IMError, e:
            logger.info('Request : %s: %s\n\n'%(e.__class__.__name__, str(e)))
            self.transport.write(bson.dumps(dict(status=dict(code=e.__class__.__name__, reason=str(e)))))
            
    def connectionLost(self, reason):
        logger.info("connectionLost - %s:%s\n%s"%(self.transport.client[0],self.transport.client[1],reason.getTraceback()))
        self.factory.handlers.remove(self)
    
    def handle(self, data):
        try:
            obj = bson.loads(data)          
        except Exception:
            logger.debug('Bad Request. Not bson protocol.')
            raise BadRequestError('Bad Request. Not bson protocol.')
        else:
            response = self.get_response(obj)
            self.transport.write(bson.dumps(response))
            
    def get_response(self, obj):
        try:
            request = IMRequest(self, obj)
            response = self.get_view(request)
        except IMError, e:
            logger.info('Request : %s: %s\n\n'%(e.__class__.__name__, str(e)))
            response = dict(status=dict(code=e.__class__.__name__, reason=str(e))) 
        else:
            response.update(dict(status=dict(code='OK', reason='OK')))
        return response
        
    def get_view(self, request):
        view, args, kwargs = self.get_resolver_match(request)
        return view(request, *args, **kwargs)
    
    def get_resolver_match(self, request):
        urlconf = settings.ROOT_URLCONF
        urlresolvers.set_urlconf(urlconf)
        MOBILE_URL_PREFIX = getattr(settings, 'MOBILE_URL_PREFIX', '^/')
        resolver = urlresolvers.RegexURLResolver(MOBILE_URL_PREFIX, urlconf)
        try:
            return resolver.resolve(request.META['PATH_INFO'])
        except Exception:
            raise InvalidParameterError('url')
        
        
class IMRequest:
    def __init__(self, handler, obj):
        self.obj = obj
        self.method = "MOBILE"
        print handler.transport.client
        self.META = dict(REQUEST_METHOD = self.method,
                         PATH_INFO = self.get_parsed_url().path,
                         QUERY_STRING = self.get_parsed_url().query,
                         REMOTE_ADDR = handler.transport.client[0]
                         )
        self.GET = self.get_GET()
        self.POST = self.get_POST()

    def get_GET(self):
        parsed_qs = parse_qs(self.get_parsed_url().query)
        for key, value in parsed_qs.copy().iteritems():
            if len(value) == 1: parsed_qs[key] = value[0]
        return parsed_qs

    def get_POST(self):
        parameters = self.obj.copy()
        del parameters['url']
        return parameters

    def get_parsed_url(self):
        if hasattr(self, '_parsed_url'): return self._parsed_url
        try:
            self._parsed_url = urlparse(self.obj['url'])
            return self._parsed_url
        except KeyError:
            raise NoParameterError('url')
        except Exception:
            raise BadRequestError('Bad url')