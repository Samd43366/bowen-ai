import sys
import os
import argparse
import asyncio

# Ensure the app module can be imported
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.firestore_services import create_user, get_user_by_email
from app.core.security import hash_password

async def seed_superadmin(email, password, name):
    from app.services.firestore_services import update_user
    
    existing = await get_user_by_email(email)

    user_data = {
        "email": email,
        "full_name": name,
        "password": hash_password(password),
        "role": "superadmin",
        "is_verified": True,
        "is_approved": True,
        "otp_code": None,
        "otp_expires_at": None,
        "is_social": False
    }

    if existing:
        print(f"User {email} already exists. Upgrading their account to Superadmin God-Mode...")
        update_user(email, user_data)
    else:
        await create_user(user_data)
    
    # create_user is synchronous in the file, we can just call it
    # wait, create_user is an async def in auth.py? Let's check. 
    # Ah, in firestore_services.py `create_user` is async.
    await create_user(user_data)
    print(f"Superadmin {email} seeded successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed superadmin into Firestore")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--name", default="Super Admin")
    args = parser.parse_args()
    
    asyncio.run(seed_superadmin(args.email, args.password, args.name))
