# # Project # #
from ..repos.user_repo import UserRepo

__all__ = ("BaseTest",)


class BaseTest:
    # # API Methods # #
    def get_user(self, user_id: str):
        return UserRepo.get(user_id=user_id)

    def list_users(self):
        return UserRepo.list()

    def create_user(self, create: dict):
        return UserRepo.create(create=create)

    def update_user(self, user_id: str, update: dict):
        UserRepo.update(user_id=user_id, update=update)

    def delete_user(self, user_id: str):
        UserRepo.delete(user_id=user_id)
