from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

raw_password = "Vinoth123"
hashed_password = pwd_context.hash(raw_password)

print(hashed_password)