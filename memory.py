"""
Memory management for Ninoclaw
"""
import json
from datetime import datetime
from config import MEMORY_FILE, MAX_MEMORY_SIZE

class Memory:
    def __init__(self):
        self.memory_file = MEMORY_FILE
        self.data = self._load()

    def _load(self):
        """Load memory from file"""
        try:
            with open(self.memory_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"conversations": {}, "user_data": {}}

    def _save(self):
        """Save memory to file"""
        with open(self.memory_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def get_conversation(self, user_id, limit=MAX_MEMORY_SIZE):
        """Get conversation history for a user"""
        key = str(user_id)
        conv = self.data["conversations"].get(key, [])
        return conv[-limit:]

    def add_message(self, user_id, role, content):
        """Add a message to conversation history"""
        key = str(user_id)

        if key not in self.data["conversations"]:
            self.data["conversations"][key] = []

        self.data["conversations"][key].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Trim if too large
        if len(self.data["conversations"][key]) > MAX_MEMORY_SIZE:
            self.data["conversations"][key] = self.data["conversations"][key][-MAX_MEMORY_SIZE:]

        self._save()

    def get_user_data(self, user_id):
        """Get stored user data"""
        key = str(user_id)
        return self.data["user_data"].get(key, {})

    def set_user_data(self, user_id, key, value):
        """Set user data (name, preferences, etc)"""
        user_key = str(user_id)

        if user_key not in self.data["user_data"]:
            self.data["user_data"][user_key] = {}

        self.data["user_data"][user_key][key] = value
        self._save()

    def get_conversation_context(self, user_id):
        """Get conversation formatted for AI (excluding system prompts)"""
        conv = self.get_conversation(user_id)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in conv
        ]

    def get_timezone(self, user_id):
        """Get user's timezone"""
        user_data = self.get_user_data(user_id)
        return user_data.get("timezone", None)

    def set_timezone(self, user_id, timezone):
        """Set user's timezone"""
        self.set_user_data(user_id, "timezone", timezone)

    def clear_conversation(self, user_id):
        """Clear conversation history for a user"""
        key = str(user_id)
        if key in self.data["conversations"]:
            self.data["conversations"][key] = []
            self._save()
