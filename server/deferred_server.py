import json

from twisted.internet import protocol, reactor, threads, defer
from twisted.protocols import basic

from server.llm.llm import setup_llm
from server.classes import PhraseMessage, SystemMessage, JSONMessage

from loguru import logger


class ClientProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.d = None

    def connectionMade(self):
        logger.debug(f"{self.factory.name} connected")
        self.factory.client = self

    def connectionLost(self, reason):
        logger.debug(f"{self.factory.name} disconnected")
            
    def runLLM(self, data, deferred):
        output = ''
        for chunk in self.factory.chain.stream(data):
            try:
                output += chunk
                message = PhraseMessage(message=output)
                self.send(message)
                # logger.debug(deferred.called)
                if deferred.called:
                    deferred.callback(output)
                    break
            except Exception as e:
                logger.error(e)
        reactor.callLater(2, threads.deferToThread, self.sendSystemMessage, 'clear')
    
    def send(self, message):
        self.factory.tasker.client.sendLine(message.dump.encode())
        
    def sendSystemMessage(self, system_message):
        logger.debug('sending system message')
        self.send(SystemMessage(message=system_message))
        

    def dataReceived(self, data):
        logger.debug(f"{self.factory.name} received data: {data}")
        if self.factory.name == "Talon":
            message = JSONMessage(dump=data)
            if message.type == 'phrase':
                self.d = defer.Deferred()
                logger.debug('Created deferred')
                t = threads.deferToThread(self.runLLM, message.message, self.d)
                def handle_cancellation(failure):
                    print("Computation was cancelled")
                self.d.associatedThread = t
                self.d.addCallback(lambda result: print("Result obtained:", result)) # TODO: This never calls
                self.d.addErrback(handle_cancellation)
                # reactor.callLater(2, cancel_computation, self.d)
            elif message.type == 'command':
                if message.message == "interrupt":
                    def cancel_computation(d):
                        d.cancel()
                    if self.d == None:
                        logger.warning('self.d is None')
                    reactor.callLater(0, cancel_computation, self.d)
                

class TalonFactory(protocol.Factory):
    def __init__(self):
        self.name = "Talon"
        self.tasker = TaskerFactory()
        self.chain = setup_llm()

    def buildProtocol(self, addr):
        return ClientProtocol(self)
    
class TaskerFactory(protocol.Factory):
    def __init__(self):
        self.name = "Tasker"
        self.client = None

    def buildProtocol(self, addr):
        return ClientProtocol(self)

def main():
    talon_port = 8000
    tasker_port = 8001

    talon_factory = TalonFactory()
    
    reactor.listenTCP(talon_port, talon_factory)
    reactor.listenTCP(tasker_port, talon_factory.tasker)

    logger.debug("Server started")
    reactor.run()

if __name__ == "__main__":
    main()
