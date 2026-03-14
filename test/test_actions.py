from intent.parser import IntentParser
from actions.action_engine import ActionEngine
from rag import RAGPipeline

parser = IntentParser()
engine = ActionEngine()
rag = RAGPipeline()

while True:

    raw = input("Command: ")
    command = rag.normalize(raw) if raw.strip() else raw
    if command != raw and command:
        print("RAG normalized:", repr(raw), "->", repr(command))

    parsed = parser.parse(command or raw)

    print("Intent:", parsed.intent)
    print("Entities:", parsed.entities)

    result = engine.execute(parsed)

    print("Result:", result)