# -*- coding:utf8 -*-
import bson
from twisted.internet import reactor, protocol

from django.conf import settings

from imdjango.network.handler import IMRequestHandler

class IMServer():

    @classmethod
    def start_server(cls, port=getattr(settings, 'MOBILE_PORT', 9338)):
        factory = protocol.ServerFactory()
        factory.protocol = IMRequestHandler
        factory.handlers = []
        reactor.listenTCP(int(port), factory)
        reactor.run()
            
if __name__ == '__main__':
    IMServer.start_server()
