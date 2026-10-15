"""Password hashing (PBKDF2-HMAC-SHA256, stdlib only) and login/signup helpers."""
import hashlib
import hmac
import os

from core import database

ITERATIONS = 200_000
MIN_PASSWORD_LEN = 6


def hash_password(password, salt_hex=None):
    salt_hex = salt_hex or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), ITERATIONS)
    return digest.hex(), salt_hex


def verify_password(password, expected_hash, salt_hex):
    candidate, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(candidate, expected_hash)


def register(name, password):
    """Returns (user_id or None, message)."""
    name = (name or "").strip()
    if not 2 <= len(name) <= 40:
        return None, "Username must be 2-40 characters."
    if len(password or "") < MIN_PASSWORD_LEN:
        return None, f"Password must be at least {MIN_PASSWORD_LEN} characters."
    if database.get_user_by_name(name):
        return None, "That username is already taken."
    h, salt = hash_password(password)
    return database.create_user(name, h, salt), "Account created."


def login(name, password):
    """Returns (user_id or None, message). Legacy v1 users (no password) set one on first login."""
    user = database.get_user_by_name(name or "")
    if user is None:
        return None, "Invalid username or password."
    if user["Password_hash"] is None:
        if len(password or "") < MIN_PASSWORD_LEN:
            return None, f"This account has no password yet - choose one ({MIN_PASSWORD_LEN}+ characters)."
        h, salt = hash_password(password)
        database.set_password(user["User_id"], h, salt)
        return user["User_id"], "Password set for your existing account."
    if verify_password(password or "", user["Password_hash"], user["Salt"]):
        return user["User_id"], "Welcome back!"
    return None, "Invalid username or password."
