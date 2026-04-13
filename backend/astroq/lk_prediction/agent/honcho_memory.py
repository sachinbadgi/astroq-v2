"""
HonchoMemory — per-client persistent memory using Honcho v3 SDK (managed or local).

Uses Honcho Cloud (app.honcho.dev) by default when HONCHO_API_KEY is set.
Falls back to a local JSON file store when Honcho is unavailable.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("astroq.agent.memory")

HONCHO_API_KEY = os.environ.get("HONCHO_API_KEY", "")
HONCHO_BASE_URL = os.environ.get("HONCHO_BASE_URL", "https://api.honcho.dev")
WORKSPACE_ID = os.environ.get("HONCHO_WORKSPACE", "astroq-lk")

# Local fallback memory directory
LOCAL_MEMORY_DIR = Path(__file__).parent.parent.parent / "data" / "memory"


class LocalMemoryFallback:
    """
    Lightweight JSON-file-backed memory when Honcho is not available.
    Stores sessions per user_id in data/memory/<user_id>.json
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        LOCAL_MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self.path = LOCAL_MEMORY_DIR / f"{user_id}.json"
        self._data = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except Exception:
                pass
        return {"messages": [], "facts": []}

    def _save(self):
        self.path.write_text(json.dumps(self._data, indent=2))

    def add_message(self, role: str, content: str):
        self._data["messages"].append({"role": role, "content": content})
        # Keep last 50 messages rolling window
        self._data["messages"] = self._data["messages"][-50:]
        self._save()

    def get_context(self) -> str:
        facts = self._data.get("facts", [])
        msgs = self._data.get("messages", [])[-6:]  # last 3 exchanges
        parts = []
        if facts:
            parts.append("Known facts about this client:\n" + "\n".join(f"- {f}" for f in facts))
        if msgs:
            history = "\n".join(f"{m['role'].upper()}: {m['content'][:200]}" for m in msgs)
            parts.append(f"Recent conversation:\n{history}")
        return "\n\n".join(parts)

    def get_history(self, last_n: int = 10) -> list:
        return self._data["messages"][-last_n:]

    def save_fact(self, fact: str):
        if fact not in self._data["facts"]:
            self._data["facts"].append(fact)
            self._data["facts"] = self._data["facts"][-20:]  # keep last 20 facts
        self._save()


class HonchoMemory:
    """
    Per-client memory backed by Honcho v3.
    Falls back to LocalMemoryFallback if Honcho is unavailable.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._backend = None
        self._honcho = None
        self._peer = None
        self._session = None
        self._use_honcho = False

        if HONCHO_API_KEY:
            try:
                self._init_honcho()
                self._use_honcho = True
                logger.info("HonchoMemory: using Honcho Cloud for user '%s'", user_id)
            except Exception as e:
                logger.warning("HonchoMemory: Honcho unavailable (%s), using local fallback", e)
                self._backend = LocalMemoryFallback(user_id)
        else:
            logger.info("HonchoMemory: HONCHO_API_KEY not set, using local JSON fallback for user '%s'", user_id)
            self._backend = LocalMemoryFallback(user_id)

    def _init_honcho(self):
        from honcho import Honcho
        self._honcho = Honcho(
            workspace_id=WORKSPACE_ID,
            base_url=HONCHO_BASE_URL,
            api_key=HONCHO_API_KEY,
        )
        self._peer = self._honcho.peer(self.user_id)
        # Use a single rolling session per user (or create if none)
        existing = list(self._peer.sessions(is_active=True))
        if existing:
            self._session = existing[0]
        else:
            self._session = self._peer.session(f"{self.user_id}-default")

    def add_message(self, role: str, content: str):
        if self._use_honcho and self._session:
            try:
                if role == "user":
                    self._session.add_messages([self._peer.message(content)])
                else:
                    # Create an assistant peer for the oracle
                    oracle = self._honcho.peer("oracle")
                    self._session.add_messages([oracle.message(content)])
                return
            except Exception as e:
                logger.warning("Honcho add_message failed: %s", e)
        self._backend.add_message(role, content)

    def get_context(self) -> str:
        if self._use_honcho and self._peer:
            try:
                response = self._peer.chat(
                    "Provide a brief summary of what you know about this client's astrological chart, "
                    "birth details, and any key astrological themes previously discussed."
                )
                return response.content if response else ""
            except Exception as e:
                logger.warning("Honcho get_context failed: %s", e)
        if self._backend:
            return self._backend.get_context()
        return ""

    def get_history(self, last_n: int = 10) -> list:
        if self._backend:
            return self._backend.get_history(last_n)
        return []

    def save_fact(self, fact: str):
        """Save a key astrological/client fact for long-term recall."""
        if self._backend:
            self._backend.save_fact(fact)
