"""
Memory Compressor for Ninoclaw
Runs nightly to compress old raw conversation logs into semantic facts to save token context and DB space.
"""
import sqlite3
import json
import time
from datetime import datetime, timedelta

from memory import DB_FILE, memory
from ai import chat

def _get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def run_compression():
    print(f"[{datetime.now()}] Starting Nightly Memory Compression...")
    conn = _get_conn()
    
    # Get all distinct users
    users = conn.execute("SELECT DISTINCT user_id FROM conversations").fetchall()
    
    # We compress anything older than 48 hours
    cutoff = datetime.now() - timedelta(hours=48)
    cutoff_str = cutoff.isoformat()
    
    for user_row in users:
        user_id = user_row["user_id"]
        
        # Pull old messages for this user
        old_msgs = conn.execute(
            "SELECT id, role, content FROM conversations WHERE user_id=? AND ts < ? ORDER BY id ASC",
            (user_id, cutoff_str)
        ).fetchall()
        
        if not old_msgs:
            continue
            
        print(f"[{datetime.now()}] Found {len(old_msgs)} old messages for user {user_id}. Compressing...")
        
        # Batch messages into chunks to avoid overwhelming the context window of the summarizer
        batch_size = 50
        batches = [old_msgs[i:i + batch_size] for i in range(0, len(old_msgs), batch_size)]
        
        for batch in batches:
            # Build conversation string
            conv_str = ""
            msg_ids = []
            for m in batch:
                msg_ids.append(m["id"])
                conv_str += f"{m['role'].capitalize()}: {m['content']}\n"
            
            system_prompt = (
                "You are an expert memory summarization agent. Your job is to read the raw conversation log below "
                "and extract long-term facts, preferences, and important context about the User.\n"
                "Return ONLY a valid JSON array of objects with 'key' and 'value'. "
                "Example: [{\"key\": \"Favorite Framework\", \"value\": \"React Native\"}, {\"key\": \"Location\", \"value\": \"New York\"}]\n"
                "If no new facts are found or it's just idle chatter, return []."
            )
            
            try:
                # Use fast smart routing to summarize
                resp = chat(message=f"Conversation Log:\n{conv_str}", system_prompt=system_prompt, force_smart=True)
                text = resp if isinstance(resp, str) else (resp.get("content") or "")
                
                # Parse JSON
                import re
                match = re.search(r'\[.*\]', text, re.DOTALL)
                if match:
                    facts = json.loads(match.group())
                    for f in facts:
                        if isinstance(f, dict) and f.get("key") and f.get("value"):
                            memory.store_fact(user_id, f["key"], str(f["value"])[:500])
                            print(f"  -> Extracted fact: {f['key']} = {f['value']}")
                            
                # Regardless of extraction success, delete the raw logs to free space
                ids_str = ",".join(str(i) for i in msg_ids)
                conn.execute(f"DELETE FROM conversations WHERE id IN ({ids_str})")
                conn.commit()
                
                # Sleep briefly to avoid hammering the LLM API on big backlogs
                time.sleep(2)
                
            except Exception as e:
                print(f"[{datetime.now()}] Failed to compress batch: {e}")
                
    conn.close()
    print(f"[{datetime.now()}] Nightly Memory Compression Complete.")

if __name__ == "__main__":
    run_compression()
