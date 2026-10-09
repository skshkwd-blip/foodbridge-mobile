"""Password helpers shared by the website login and the mobile app login."""
import hmac

from werkzeug.security import check_password_hash, generate_password_hash


def hash_pw(password):
    return generate_password_hash(str(password).strip())


def check_pw(stored, given):
    """True if `given` matches `stored`. Accepts hashes and, for old rows, plain text."""
    if not stored or not given:
        return False
    stored, given = str(stored).strip(), str(given).strip()
    if stored.startswith(("scrypt:", "pbkdf2:")):
        return check_password_hash(stored, given)
    return hmac.compare_digest(stored.encode(), given.encode())   # legacy plain-text rows
