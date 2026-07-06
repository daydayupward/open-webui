import sqlite3
import json

db_path = '/home/eason/proj/open-webui/backend/data/webui.db'

def inspect_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, user_id, title, updated_at FROM chat ORDER BY updated_at DESC LIMIT 5;")
    chats = cursor.fetchall()
    for chat in chats:
        print(f"Chat ID: {chat[0]} | User: {chat[1]} | Title: '{chat[2]}' | Updated: {chat[3]}")
        try:
            cursor.execute("SELECT chat FROM chat WHERE id = ?;", (chat[0],))
            chat_data_str = cursor.fetchone()[0]
            chat_data = json.loads(chat_data_str)
            messages = chat_data.get('messages', [])
            print(f"  Total messages: {len(messages)}")
            for msg in messages[-4:]: 
                role = msg.get('role')
                content = msg.get('content')
                short_content = content[:150] + '...' if content and len(content) > 150 else content
                print(f"    [{role}]: {short_content}")
        except Exception as e:
            print(f"  Error reading chat data: {e}")
            
    conn.close()

if __name__ == '__main__':
    inspect_db()
