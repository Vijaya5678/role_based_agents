import os
import sys
import sqlite3
import sys
import os

# Set root path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from shared.storage.handle_user import validate_login, get_all_users, get_user

print("📋 All Users in DB:")
users = get_all_users()
for user in users:
    print(f"👤 {user}")

print("\n🔐 Testing Login:")
test_user_id = "vijaya01"
test_password = "vijaya@123"

if validate_login(test_user_id, test_password):
    user = get_user(test_user_id)
    print(f"✅ Login successful! Welcome {user[1]} ({user[0]})")
else:
    print(f"❌ Invalid credentials for: {test_user_id}")
