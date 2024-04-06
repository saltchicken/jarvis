from twisted.internet import protocol, reactor
from twisted.protocols import basic

from llm import setup_llm
# global clients
# clients = []
class ClientProtocol(basic.LineReceiver):
    def __init__(self, factory):
        self.factory = factory

    def connectionMade(self):
        print(f"{self.factory.name} connected")
        self.factory.thing = self

    def connectionLost(self, reason):
        print(f"{self.factory.name} disconnected")

    # def lineReceived(self, line):
    #     print("Received:", line)
    #     # for client in self.factory.clients:
    #     #     if client != self:
    #     #         client.sendLine(line.encode())

    def runLLM(self, phrase):
        print(f"Running LLM: on {phrase}")

    def dataReceived(self, data):
        print(f"{self.factory.name} received data: {data}")
        if self.factory.name == "Talon":
            # self.factory.tasker.thing.transport.write(data.encode())
            self.factory.tasker.thing.transport.write(data)


class TalonFactory(protocol.Factory):
    def __init__(self):
        self.name = "Talon"
        self.tasker = TaskerFactory()

    def buildProtocol(self, addr):
        return ClientProtocol(self)
    
class TaskerFactory(protocol.Factory):
    def __init__(self):
        self.name = "Tasker"
        self.thing = None
        
        self.chain = setup_llm()

    def buildProtocol(self, addr):
        return ClientProtocol(self)

def main():
    # Port for client 1
    talon_port = 8000
    # Port for client 2
    tasker_port = 8001

    # Create factory instances
    talon_factory = TalonFactory()

    # clients.append(talon_factory)
    # clients.append(tasker_factory)

    # Start listening for client connections on respective ports
    reactor.listenTCP(talon_port, talon_factory)
    reactor.listenTCP(tasker_port, talon_factory.tasker)

    print("Server started")
    reactor.run()

if __name__ == "__main__":
    main()
