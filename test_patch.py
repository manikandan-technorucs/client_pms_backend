import bcrypt
class _About:
    __version__ = "4.0.0"
bcrypt.__about__ = _About()

from passlib.context import CryptContext
c = CryptContext(schemes=["bcrypt"])
try:
    print(c.hash("test"))
except Exception as e:
    import traceback
    traceback.print_exc()
