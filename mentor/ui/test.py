import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'core')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'shared', 'storage')))
# This allows the script to find your 'handle_mentor_chat_history' module
# It assumes you run this script from your project's root directory.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'shared', 'storage')))

from shared.storage.handle_mentor_chat_history import get_chat_messages_with_state, init_db

def test_database_fetch():
    """
    Directly tests the get_chat_messages_with_state function.
    """
    # --- IMPORTANT ---
    # Use a user_id and title that you KNOW exists in your database.
    test_user_id = "vijaya01"
    test_chat_title = "AI_20250724102928_fde7" # The exact title from your logs

    print("--- Testing Database Connection ---")
    print(f"Querying for user_id: '{test_user_id}' and title: '{test_chat_title}'\n")

    try:
        # Ensure the DB and tables exist
        init_db()

        # Call the function directly
        result = get_chat_messages_with_state(test_user_id, test_chat_title)

        # Check the result
        if result:
            print("✅ Success! Data was found in the database.")
            messages, state = result
            
            print("\n--- Messages ---")
            print(json.dumps(messages, indent=2))
            
            print("\n--- State ---")
            print(json.dumps(state, indent=2))
        else:
            print("❌ No data found for this user_id and title.")
            print("Verify that these exact values exist in your 'chats' table.")

    except ImportError as e:
        print(f"🚨 Import Error: {e}")
        print("Please ensure you are running this script from your project's root directory.")
    except Exception as e:
        print(f"🚨 An error occurred: {e}")

if __name__ == "__main__":
    test_database_fetch()