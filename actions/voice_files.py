import os
import subprocess
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FileActions:

    def handle(self, entities, parsed_intent=None):

        action = entities.get("action")

        if action == "create":
            return self.create_file(entities)

        elif action == "write":
            return self.write_to_active(entities)

        elif action == "delete":
            return self.delete_file(entities)

        elif action == "open":
            return self.open_file(entities)

        return {
            "success": False,
            "response_text": f"DOCS action '{action}' not supported yet",
            "intent": getattr(parsed_intent, "intent", "DOCS") if parsed_intent else "DOCS",
            "entities": entities,
        }

    # ─────────────────────────────
    # CREATE
    # ─────────────────────────────

    def create_file(self, entities):

        name = entities.get("name") or entities.get("filename")

        if not name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            name = f"document_{timestamp}.txt"

        path = os.path.join(os.getcwd(), name)

        try:

            with open(path, "w") as f:
                pass

            subprocess.Popen(["notepad", path])

            logger.info("Created file %s", path)

            return {
                "success": True,
                "path": path,
                "response_text": f"Created {name}",
            }

        except Exception as e:

            logger.error("Create file failed: %s", e)

            return {
                "success": False,
                "response_text": str(e)
            }

    # ─────────────────────────────
    # DELETE
    # ─────────────────────────────

    def delete_file(self, entities):

        name = entities.get("name") or entities.get("filename")

        if not name:
            return {
                "success": False,
                "response_text": "No file name provided"
            }

        path = os.path.join(os.getcwd(), name)

        try:

            if os.path.exists(path):
                os.remove(path)

                logger.info("Deleted file %s", path)

                return {
                    "success": True,
                    "response_text": f"Deleted {name}"
                }

            return {
                "success": False,
                "response_text": "File not found"
            }

        except Exception as e:

            logger.error("Delete file failed: %s", e)

            return {
                "success": False,
                "response_text": str(e)
            }

    # ─────────────────────────────
    # OPEN
    # ─────────────────────────────

    def open_file(self, entities):

        name = entities.get("name") or entities.get("filename")

        if not name:
            return {
                "success": False,
                "response_text": "No file name provided"
            }

        path = os.path.join(os.getcwd(), name)

        try:

            if os.path.exists(path):

                subprocess.Popen(["notepad", path])

                logger.info("Opened file %s", path)

                return {
                    "success": True,
                    "response_text": f"Opened {name}",
                    "path": path,
                }

            return {
                "success": False,
                "response_text": "File not found"
            }

        except Exception as e:

            logger.error("Open file failed: %s", e)

            return {
                "success": False,
                "response_text": str(e)
            }

    # ─────────────────────────────
    # WRITE (dictate into active window)
    # ─────────────────────────────

    def write_to_active(self, entities):
        content = (entities.get("content") or "").strip()
        if not content:
            return {
                "success": False,
                "response_text": "Nothing to write. Please say what you want to type."
            }
        try:
            import pyautogui
            pyautogui.typewrite(content + " ", interval=0.04)
            logger.info("Typed %d chars into active window", len(content))
            return {"success": True, "response_text": "Done."}
        except Exception as e:
            logger.error("Write to active failed: %s", e)
            return {
                "success": False,
                "response_text": "Could not type that text into the active window."
            }