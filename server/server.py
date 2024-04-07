import json

from twisted.internet import protocol, reactor, threads, defer
from twisted.protocols import basic

from server.llm.llm import setup_llm
from server.classes import PhraseMessage, SystemMessage, JSONMessage

from loguru import logger


class TalonProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.d = None

    def connectionMade(self):
        logger.debug(f"Talon connected")
        self.factory.client = self

    def connectionLost(self, reason):
        logger.debug(f"Talon disconnected")
            
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
        # TODO: Make a function explicitly for calling after LLM stream is done
        logger.debug('LLM thread complete')
        # reactor.callLater(6, threads.deferToThread, self.sendSystemMessage, 'clear')
    
    def send(self, message):
        self.factory.tasker.client.sendLine(message.dump.encode())
        
    def sendSystemMessage(self, system_message):
        logger.debug('sending system message')
        self.send(SystemMessage(message=system_message))
        

    def dataReceived(self, data):
        logger.debug(f"Talon received data: {data}")
        message = JSONMessage(dump=data)
        if message.type == 'phrase':
            self.factory.d = defer.Deferred()
            logger.debug('Created deferred')
            t = threads.deferToThread(self.runLLM, message.message, self.factory.d)
            self.factory.d.associatedThread = t
            self.factory.d.addCallback(lambda result: print("Result obtained:", result)) # TODO: This never calls
            self.factory.d.addErrback(lambda result: print(f"Cancellation Received"))
        elif message.type == 'command':
            if message.message == "stop":
                if self.factory.d == None:
                    logger.warning('self.d is None')
                else:
                    self.factory.d.cancel()
            elif message.message == 'clear':
                reactor.callLater(0, threads.deferToThread, self.sendSystemMessage, 'clear')
                    
class TaskerProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory
        self.d = None

    def connectionMade(self):
        logger.debug(f"Tasker connected")
        self.factory.client = self

    def connectionLost(self, reason):
        logger.debug(f"Tasker disconnected")
            
    # def runLLM(self, data, deferred):
    #     output = ''
    #     for chunk in self.factory.chain.stream(data):
    #         try:
    #             output += chunk
    #             message = PhraseMessage(message=output)
    #             self.send(message)
    #             # logger.debug(deferred.called)
    #             if deferred.called:
    #                 deferred.callback(output)
    #                 break
    #         except Exception as e:
    #             logger.error(e)
    #     # TODO: Make a function explicitly for calling after LLM stream is done
    #     logger.debug('LLM thread complete')
    #     # reactor.callLater(6, threads.deferToThread, self.sendSystemMessage, 'clear')
    
    # def send(self, message):
    #     self.factory.tasker.client.sendLine(message.dump.encode())
        
    # def sendSystemMessage(self, system_message):
    #     logger.debug('sending system message')
    #     self.send(SystemMessage(message=system_message))
        

    def dataReceived(self, data):
        logger.debug(f"Tasker received data: {data}")
        # if self.factory.name == "Talon":
        #     message = JSONMessage(dump=data)
        #     if message.type == 'phrase':
        #         self.factory.d = defer.Deferred()
        #         t = threads.deferToThread(self.runLLM, message.message, self.factory.d)
        #         self.factory.d.associatedThread = t
        #         self.factory.d.addCallback(lambda result: print("Result obtained:", result)) # TODO: This never calls
        #         self.factory.d.addErrback(lambda result: print(f"Cancellation Received"))
        #     elif message.type == 'command':
        #         if message.message == "stop":
        #             if self.factory.d == None:
        #                 logger.warning('self.d is None')
        #             else:
        #                 self.factory.d.cancel()
        #         elif message.message == 'clear':
        #             reactor.callLater(0, threads.deferToThread, self.sendSystemMessage, 'clear')
                

class TalonFactory(protocol.Factory):
    def __init__(self):
        self.tasker = TaskerFactory()
        self.chain = setup_llm()
        self.d = None

    def buildProtocol(self, addr):
        return TalonProtocol(self)
    
class TaskerFactory(protocol.Factory):
    def __init__(self):
        self.client = None

    def buildProtocol(self, addr):
        return TaskerProtocol(self)

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
