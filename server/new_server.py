import json

from twisted.internet import protocol, reactor
from twisted.protocols import basic

from server.llm.llm import setup_llm


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
        output = ''
        for chunk in self.factory.chain.stream(phrase):
            output += chunk
            data = {"type": "phrase", "message": output}
            data_string = json.dumps(data)
            # client_socket.sendall(data_string.encode())
            # self.factory.tasker.thing.transport.write(data_string.encode())
            self.factory.tasker.thing.transport.sendLine(output.encode())


    def dataReceived(self, data):
        print(f"{self.factory.name} received data: {data}")
        if self.factory.name == "Talon":
            packet = json.loads(data)
            if packet['type'] == 'phrase':
                self.runLLM(packet['message'])
            # self.factory.tasker.thing.transport.write(data.encode())
            # self.factory.tasker.thing.transport.write(data)


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
