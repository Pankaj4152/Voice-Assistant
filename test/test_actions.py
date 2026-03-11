from intent.parser import IntentParser
from actions.action_engine import ActionEngine


parser = IntentParser()
engine = ActionEngine()

while True:

    command = input("Command: ")

    parsed = parser.parse(command)

    print("Intent:", parsed.intent)
    print("Entities:", parsed.entities)

    result = engine.execute(parsed)

    print("Result:", result)