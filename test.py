# from telemetry.logger import TelemetryLogger
# import time

# logger = TelemetryLogger()

# start = time.time()
# time.sleep(0.2)

# logger.log_event("ASR", "Transcription started")
# logger.log_latency("ASR", start)

# try:
#     1 / 0
# except Exception as e:
#     logger.log_error("TEST", e)









from voice.asr import WhisperASR
# from intent.classifier import IntentClassifier
# from actions.windows_executor import WindowsExecutor
from telemetry.logger import TelemetryLogger


def main():
    logger = TelemetryLogger()

    asr = WhisperASR(logger=logger)

    print("Press Ctrl+C to exit.\n")

    while True:
        input("Press ENTER to record...")
        text = asr.transcribe()
        print("Returned text:", text)


if __name__ == "__main__":
    main()




# from sarvamai import SarvamAI
# from dotenv import load_dotenv
# import os
# load_dotenv()
# client = SarvamAI(
#     api_subscription_key=os.getenv("SARVAM_API_KEY"),
# )

# response = client.text.translate(
#     input="Hi, My Name is Vinayak.",
#     source_language_code="auto",
#     target_language_code="gu-IN",
#     speaker_gender="Male"
# )

# print(response)
