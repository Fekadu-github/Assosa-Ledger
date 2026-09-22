"""
Run this once, from your own computer, pointed at your deployed database,
to create the very first login (you, as 'owner'). After that, you can
create further accounts (your friend, a geologist, etc.) either by
running this script again or by logging in and calling POST /auth/users.

Usage:
    export DATABASE_URL=postgresql://...   # same value as on Render
    pip install sqlalchemy psycopg2-binary passlib[bcrypt]
    python create_user.py
"""
import getpass
import os
import sys

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(__file__))
from main import Base, User  # noqa: E402

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./assosa_ledger.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(bind=engine)
Session = sessionmaker(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def main():
    db = Session()
    username = input("Username: ").strip()
    if db.query(User).filter(User.username == username).first():
        print(f"'{username}' already exists.")
        return
    name = input("Full name: ").strip()
    role = input("Role [owner/gm/geologist/viewer] (default: owner): ").strip() or "owner"
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords did not match.")
        return
    user = User(username=username, name=name, role=role, password_hash=pwd_context.hash(password))
    db.add(user)
    db.commit()
    print(f"Created user '{username}' with role '{role}'.")


if __name__ == "__main__":
    main()
