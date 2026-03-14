"""
actions/voice_file_nav.py
─────────────────────────
Voice-driven file navigation and management.

Handles:
  list_folder   — speak contents of a folder (up to 10 items)
  open_folder   — open a folder in Windows Explorer
  go_to_folder  — change cwd + open in Explorer
  move_file     — move a file to another folder
  copy_file     — copy a file to another folder
  rename_file   — rename a file
  find_file     — search common user folders by name
  delete_file   — send to Recycle Bin (recoverable), fallback to remove

Security:
  - All operations validate the file/folder is within the user's home tree or cwd.
  - No path traversal (../) is allowed.
  - System-critical paths are blocked.
"""

import ctypes
import logging
import os
import re
import shutil
import subprocess
from ctypes import wintypes
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── Known folder name → absolute path ────────────────────────────────────────

def _pick_existing_path(candidates: list[Path], default: Path) -> str:
    for candidate in candidates:
        try:
            if candidate.exists():
                return str(candidate)
        except Exception:
            continue
    return str(default)


def _build_known_folders() -> dict[str, str]:
    home = Path.home()
    user_profile = Path(os.environ.get("USERPROFILE") or str(home))
    one_drive = Path(os.environ.get("OneDrive") or "")

    def _candidates(name: str) -> list[Path]:
        paths = [home / name, user_profile / name]
        if str(one_drive):
            paths.append(one_drive / name)
        return paths

    return {
        "desktop": _pick_existing_path(_candidates("Desktop"), home / "Desktop"),
        "downloads": _pick_existing_path(_candidates("Downloads"), home / "Downloads"),
        "documents": _pick_existing_path(_candidates("Documents"), home / "Documents"),
        "pictures": _pick_existing_path(_candidates("Pictures"), home / "Pictures"),
        "music": _pick_existing_path(_candidates("Music"), home / "Music"),
        "videos": _pick_existing_path(_candidates("Videos"), home / "Videos"),
        "home": str(home),
    }


_KNOWN_FOLDERS: dict[str, str] = _build_known_folders()

_FOLDER_ALIASES = {
    "deskhtop": "desktop",
    "deshtop": "desktop",
    "deskop": "desktop",
    "dowloads": "downloads",
    "download": "downloads",
    "document": "documents",
    "doc": "documents",
}

# Paths that must never be touched for safety
_BLOCKED_PATHS = {
    str(Path("C:/Windows")).lower(),
    str(Path("C:/Windows/System32")).lower(),
    str(Path("C:/Program Files")).lower(),
    str(Path("C:/Program Files (x86)")).lower(),
}

_SEARCH_ROOTS: list[str] = list(_KNOWN_FOLDERS.values())


class FileNavActions:
    """Voice-driven file navigation and management."""

    # ── Security helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _is_safe_path(path: str) -> bool:
        """Block paths outside the user home tree and known dangerous locations."""
        try:
            resolved = str(Path(path).resolve()).lower()
            home = str(Path.home().resolve()).lower()
            # Must be inside home OR the current working directory
            cwd = str(Path(os.getcwd()).resolve()).lower()
            inside_home = resolved.startswith(home)
            inside_cwd = resolved.startswith(cwd)
            for blocked in _BLOCKED_PATHS:
                if resolved.startswith(blocked):
                    return False
            return inside_home or inside_cwd
        except Exception:
            return False

    @staticmethod
    def _resolve_folder(name: str) -> Optional[str]:
        """Map a spoken folder name to an absolute path. Returns None if not found."""
        key = name.strip().lower()
        key = _FOLDER_ALIASES.get(key, key)
        if key in _KNOWN_FOLDERS:
            return _KNOWN_FOLDERS[key]
        # Try cwd-relative
        candidate = os.path.join(os.getcwd(), name)
        if os.path.isdir(candidate):
            return candidate
        # Try home-relative
        candidate = str(Path.home() / name)
        if os.path.isdir(candidate):
            return candidate
        return None

    def _locate_file(self, filename: str) -> Optional[str]:
        """
        Find a file by name (case-insensitive, partial-friendly).
        Search order: cwd (recursive), then known common folders (recursive).
        Returns the first match or None.
        """
        query = filename.strip().strip('"').strip("'")
        if not query:
            return None

        query_lower = query.lower()
        query_stem = Path(query_lower).stem
        search_dirs = [os.getcwd()] + _SEARCH_ROOTS

        exact_match: Optional[str] = None
        stem_match: Optional[str] = None
        partial_match: Optional[str] = None

        for folder in search_dirs:
            if not os.path.isdir(folder):
                continue
            try:
                for root, _, files in os.walk(folder):
                    for name in files:
                        name_lower = name.lower()
                        full_path = os.path.join(root, name)
                        if name_lower == query_lower:
                            return full_path
                        if query_stem and Path(name_lower).stem == query_stem and stem_match is None:
                            stem_match = full_path
                        if query_lower in name_lower and partial_match is None:
                            partial_match = full_path
                    # Keep traversal bounded for responsiveness.
                    if stem_match and partial_match:
                        break
            except (PermissionError, OSError):
                continue

            if exact_match:
                return exact_match

        if stem_match:
            return stem_match
        if partial_match:
            return partial_match
        return None

    # ── Public action handlers ────────────────────────────────────────────────

    def list_folder(self, entities: dict) -> dict:
        """Speak the contents of a folder (up to 10 items)."""
        folder_name = (entities.get("folder") or "").strip()
        folder_path = (
            self._resolve_folder(folder_name) if folder_name else os.getcwd()
        )

        if not folder_path or not os.path.isdir(folder_path):
            return {
                "success": False,
                "response_text": f"I could not find the {folder_name or 'current'} folder.",
            }

        try:
            raw_entries = sorted(os.listdir(folder_path))
        except PermissionError:
            return {
                "success": False,
                "response_text": "I don't have permission to read that folder.",
            }

        if not raw_entries:
            return {
                "success": True,
                "response_text": f"The {folder_name or 'current'} folder is empty.",
                "entries": [],
            }

        visible = raw_entries[:10]
        remaining = len(raw_entries) - len(visible)
        spoken = ", ".join(visible)
        tail = f", and {remaining} more" if remaining else ""
        display = folder_name or os.path.basename(folder_path)

        return {
            "success": True,
            "response_text": f"{display} contains: {spoken}{tail}.",
            "entries": raw_entries,
            "folder_path": folder_path,
        }

    def open_folder(self, entities: dict) -> dict:
        """Open a folder in Windows Explorer."""
        folder_name = (entities.get("folder") or "").strip()
        folder_path = (
            self._resolve_folder(folder_name) if folder_name else str(Path.home())
        )

        if not folder_path or not os.path.isdir(folder_path):
            return {
                "success": False,
                "response_text": f"I could not find the {folder_name or 'home'} folder.",
            }

        try:
            subprocess.Popen(["explorer", folder_path])
            display = folder_name or os.path.basename(folder_path)
            return {
                "success": True,
                "response_text": f"Opened {display} folder.",
                "folder_path": folder_path,
            }
        except Exception as e:
            logger.error("Open folder failed: %s", e)
            return {"success": False, "response_text": "Failed to open the folder."}

    def go_to_folder(self, entities: dict) -> dict:
        """Change working directory to a folder and open it in Explorer."""
        folder_name = (entities.get("folder") or "").strip()
        folder_path = (
            self._resolve_folder(folder_name) if folder_name else str(Path.home())
        )

        if not folder_path or not os.path.isdir(folder_path):
            return {
                "success": False,
                "response_text": f"I could not find the {folder_name} folder.",
            }

        try:
            os.chdir(folder_path)
            subprocess.Popen(["explorer", folder_path])
            display = folder_name or os.path.basename(folder_path)
            return {
                "success": True,
                "response_text": f"Navigated to {display}.",
            }
        except Exception as e:
            logger.error("Go to folder failed: %s", e)
            return {"success": False, "response_text": "Could not navigate to that folder."}

    def move_file(self, entities: dict) -> dict:
        """Move a file to a destination folder."""
        filename = (entities.get("filename") or entities.get("name") or "").strip()
        dest_name = (entities.get("dest") or entities.get("destination") or "").strip()

        if not filename:
            return {"success": False, "response_text": "Please tell me which file to move."}
        if not dest_name:
            return {"success": False, "response_text": "Please tell me where to move it."}

        dest_path = self._resolve_folder(dest_name)
        if not dest_path:
            return {"success": False, "response_text": f"I could not find the {dest_name} folder."}

        src_path = self._locate_file(filename)
        if not src_path:
            return {"success": False, "response_text": f"I could not find the file {filename}."}

        if not self._is_safe_path(src_path) or not self._is_safe_path(dest_path):
            return {"success": False, "response_text": "That operation is not allowed for safety reasons."}

        try:
            target = os.path.join(dest_path, os.path.basename(src_path))
            shutil.move(src_path, target)
            logger.info("Moved %s → %s", src_path, target)
            return {"success": True, "response_text": f"Moved {filename} to {dest_name}."}
        except Exception as e:
            logger.error("Move file failed: %s", e)
            return {"success": False, "response_text": f"Failed to move {filename}."}

    def copy_file(self, entities: dict) -> dict:
        """Copy a file to a destination folder."""
        filename = (entities.get("filename") or entities.get("name") or "").strip()
        dest_name = (entities.get("dest") or entities.get("destination") or "").strip()

        if not filename:
            return {"success": False, "response_text": "Please tell me which file to copy."}
        if not dest_name:
            return {"success": False, "response_text": "Please tell me where to copy it."}

        dest_path = self._resolve_folder(dest_name)
        if not dest_path:
            return {"success": False, "response_text": f"I could not find the {dest_name} folder."}

        src_path = self._locate_file(filename)
        if not src_path:
            return {"success": False, "response_text": f"I could not find the file {filename}."}

        if not self._is_safe_path(src_path) or not self._is_safe_path(dest_path):
            return {"success": False, "response_text": "That operation is not allowed for safety reasons."}

        try:
            target = os.path.join(dest_path, os.path.basename(src_path))
            shutil.copy2(src_path, target)
            logger.info("Copied %s → %s", src_path, target)
            return {"success": True, "response_text": f"Copied {filename} to {dest_name}."}
        except Exception as e:
            logger.error("Copy file failed: %s", e)
            return {"success": False, "response_text": f"Failed to copy {filename}."}

    def rename_file(self, entities: dict) -> dict:
        """Rename a file."""
        filename = (entities.get("filename") or entities.get("name") or "").strip()
        new_name = (entities.get("new_name") or "").strip()

        if not filename:
            return {"success": False, "response_text": "Please tell me which file to rename."}
        if not new_name:
            return {"success": False, "response_text": "Please tell me the new name."}

        src_path = self._locate_file(filename)
        if not src_path:
            return {"success": False, "response_text": f"I could not find the file {filename}."}

        new_path = os.path.join(os.path.dirname(src_path), new_name)

        if not self._is_safe_path(src_path):
            return {"success": False, "response_text": "That operation is not allowed for safety reasons."}

        try:
            os.rename(src_path, new_path)
            logger.info("Renamed %s → %s", src_path, new_path)
            return {"success": True, "response_text": f"Renamed {filename} to {new_name}."}
        except Exception as e:
            logger.error("Rename failed: %s", e)
            return {"success": False, "response_text": f"Failed to rename {filename}."}

    def find_file(self, entities: dict) -> dict:
        """Search for a file by name across common user folders."""
        filename = (
            entities.get("filename") or entities.get("name") or entities.get("query") or ""
        ).strip()
        folder_hint = (entities.get("folder") or "").strip().lower()

        if not filename:
            return {"success": False, "response_text": "Please tell me the file name to search for."}

        matches: list[str] = []
        filename_lower = filename.lower()

        search_roots = list(_SEARCH_ROOTS)
        hinted = self._resolve_folder(folder_hint) if folder_hint else None
        if hinted and hinted not in search_roots:
            search_roots.insert(0, hinted)

        for root in search_roots:
            if not os.path.isdir(root):
                continue
            try:
                for walk_root, _, files in os.walk(root):
                    for name in files:
                        if filename_lower in name.lower():
                            matches.append(os.path.join(walk_root, name))
                            if len(matches) >= 5:
                                break
                    if len(matches) >= 5:
                        break
            except (PermissionError, OSError):
                continue
            if len(matches) >= 5:
                break

        if not matches:
            return {
                "success": True,
                "response_text": f"No file matching {filename} was found in your common folders.",
                "matches": [],
            }

        spoken = ", ".join(
            f"{os.path.basename(m)} in {os.path.basename(os.path.dirname(m))}"
            for m in matches[:3]
        )
        tail = f", and {len(matches) - 3} more" if len(matches) > 3 else ""

        return {
            "success": True,
            "response_text": f"Found: {spoken}{tail}.",
            "matches": matches,
        }

    def delete_file(self, entities: dict) -> dict:
        """Delete a file. Sends to Recycle Bin via Windows shell (recoverable)."""
        filename = (entities.get("filename") or entities.get("name") or "").strip()

        if not filename:
            return {"success": False, "response_text": "Please tell me which file to delete."}

        src_path = self._locate_file(filename)
        if not src_path:
            return {"success": False, "response_text": f"I could not find the file {filename}."}

        if not self._is_safe_path(src_path):
            return {"success": False, "response_text": "That operation is not allowed for safety reasons."}

        # Use Windows shell to send to Recycle Bin (recoverable)
        try:
            class SHFILEOPSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("hwnd",                    wintypes.HWND),
                    ("wFunc",                   wintypes.UINT),
                    ("pFrom",                   wintypes.LPCWSTR),
                    ("pTo",                     wintypes.LPCWSTR),
                    ("fFlags",                  wintypes.WORD),
                    ("fAnyOperationsAborted",   wintypes.BOOL),
                    ("hNameMappings",           ctypes.c_void_p),
                    ("lpszProgressTitle",       wintypes.LPCWSTR),
                ]

            op = SHFILEOPSTRUCT()
            op.wFunc = 3          # FO_DELETE
            op.pFrom = src_path + "\0\0"
            op.fFlags = 0x0040 | 0x0010  # FOF_ALLOWUNDO | FOF_NOCONFIRMATION
            result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
            if result == 0:
                logger.info("Sent to Recycle Bin: %s", src_path)
                return {"success": True, "response_text": f"Moved {filename} to the Recycle Bin."}
        except Exception as shell_err:
            logger.warning("Shell delete failed, falling back: %s", shell_err)

        # Hard fallback
        try:
            os.remove(src_path)
            logger.info("Deleted %s", src_path)
            return {"success": True, "response_text": f"Deleted {filename}."}
        except Exception as e:
            logger.error("Delete failed: %s", e)
            return {"success": False, "response_text": f"Failed to delete {filename}."}
