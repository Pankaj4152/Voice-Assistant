def open_path(self, entities):
        """
        Open any file or folder path.
        - If it's a folder  → open in Explorer
        - If it's a file    → open with its default associated app (os.startfile)
        - Supports env-var expansion and ~ home dir
        """
        raw = (entities.get("path") or entities.get("target") or "").strip()
        if not raw:
            return {"success": False, "response_text": "No path specified."}

        path = os.path.expandvars(os.path.expanduser(raw))

        if not os.path.exists(path):
            # Try to locate the item inside common roots as a fallback
            found = self._search_path_hierarchy(raw)
            if found:
                path = found
            else:
                return {
                    "success": False,
                    "response_text": f"Could not find '{raw}'. Please check the path.",
                }

        try:
            if os.path.isdir(path):
                subprocess.Popen(f'explorer "{path}"', shell=True)
                logger.info("Opened folder: %s", path)
                return {"success": True, "response_text": f"Opening folder: {os.path.basename(path) or path}"}
            else:
                os.startfile(path)
                logger.info("Opened file: %s", path)
                return {"success": True, "response_text": f"Opening {os.path.basename(path)}"}
        except Exception as e:
            logger.error("open_path failed for %s: %s", path, e)
            return {"success": False, "response_text": f"Failed to open '{os.path.basename(path)}'."}

from actions.os_actions import OSActions
actions = OSActions()
actions.open_path({"path": "C:\\Users\\Michael\\Desktop"})
