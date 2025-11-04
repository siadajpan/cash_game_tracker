from passlib.context import CryptContext

# bcrypt_sha256 automatically hashes the password with SHA256 before bcrypt,
# so we don't need to manually truncate anything.
pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


class Hasher:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)
