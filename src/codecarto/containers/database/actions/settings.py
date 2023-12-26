"""SETTINGS
Settings loaders using Pydantic BaseSettings classes (load from environment variables / dotenv file)
"""

# # Installed # #
import pydantic

__all__ = ("api_settings", "mongo_settings")


class BaseSettings(pydantic.BaseSettings):
    class Config:
        env_file = ".env"


class MongoSettings(BaseSettings):
    uri: str = "mongodb://127.0.0.1:27017"
    database: str = "fastapi+pydantic+mongo-example"
    collection: str = "codecarto"

    class Config(BaseSettings.Config):
        env_prefix = "MONGO_"


mongo_settings = MongoSettings()
