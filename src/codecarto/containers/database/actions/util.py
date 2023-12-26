def hash_password(password: str) -> str:
    """Hash a password.

    Parameters
    ----------
    password: str
        password to hash

    Returns
    -------
    str:
        hashed password
    """
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def random_id() -> str:
    """Return a random ObjectID id.

    Returns
    -------
    str:
        a random ObjectID id
    """
    from bson import ObjectId

    return str(ObjectId())
