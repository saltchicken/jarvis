import json

from twisted.internet import protocol, reactor, threads
from twisted.protocols import basic

from server.llm.llm import setup_llm
from server.classes import PhraseMessage, JSONMessage

from loguru import logger


class ClientProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        logger.debug(f"{self.factory.name} connected")
        self.factory.client = self

    def connectionLost(self, reason):
        logger.debug(f"{self.factory.name} disconnected")
            
    def runLLM(self, data):
        output = ''
        for chunk in self.factory.chain.stream(data):
            output += chunk
            message = PhraseMessage(message=output)
            self.factory.tasker.client.sendLine(message.dump.encode())

    def dataReceived(self, data):
        logger.debug(f"{self.factory.name} received data: {data}")
        if self.factory.name == "Talon":
            message = JSONMessage(dump=data)
            print(message)
            if message.type == 'phrase':
                d = threads.deferToThread(self.runLLM, message.message)
                

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
