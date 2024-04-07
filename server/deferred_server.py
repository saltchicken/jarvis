import json

from twisted.internet import protocol, reactor, threads, defer
from twisted.protocols import basic

from server.llm.llm import setup_llm
from server.classes import PhraseMessage, SystemMessage, JSONMessage

from loguru import logger


class ClientProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory

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
                self.debug(deferred.called)
                # if not deferred.called:
                #     deferred.callback(output)
            except Exception as e:
                print(e)
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
                self.m = defer.Deferred()
                d = threads.deferToThread(self.runLLM, message.message, self.m)
                def cancel_computation(d):
                    # Cancel the Deferred object
                    d.cancel()
                def handle_cancellation(failure):
                    # Print a message indicating that the computation was cancelled
                    print("Computation was cancelled")
                self.m.associatedThread = d
                self.m.addCallback(lambda result: print("Result obtained:", result))
                self.m.addErrback(handle_cancellation)
                reactor.callLater(3, cancel_computation, self.m)
                

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
