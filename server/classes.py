from dataclasses import dataclass
import json

@dataclass
class JSONMessage:
    type: str = None
    message: str = None
    dump: str = None

    def __post_init__(self):
        if self.dump is not None:
            dump = json.loads(self.dump)
            self.type = dump['type']
            self.message = dump['message']
        else:
            dump = {"type": self.type, "message": self.message}
            self.dump = json.dumps(dump)
    
@dataclass
class PhraseMessage(JSONMessage):
    type: str = 'phrase'
    
@dataclass
class SystemMessage(JSONMessage):
    type: str = 'system'
    
@dataclass
class CommandMessage(JSONMessage):
    type: str = 'command'


if __name__ == "__main__":
    # Example usage:
    data1 = JSONMessage(type="Test", message="Hello, world!")
    print(data1)  # Output: {"type": "phrase", "message": "Hello, world!"}

    # data2 = JSONMessage(type="Test", dump='{"type": "Test", "message": "Hello, world!", "dump": null}')
    # print(data2)  # Output: {"type": "phrase", "message": "Hello, world!"}


    phrase = PhraseMessage(message="I am the message")
    print(phrase)

    test = {"type": "phrase", "message": "This works"}
    test_dump = json.dumps(test)
    result = PhraseMessage(dump=test_dump)
    print(result)

    # data2 = JSONData(dump='{"type": "error", "message": "Invalid input"}')
    # Output: Initializing from dump
