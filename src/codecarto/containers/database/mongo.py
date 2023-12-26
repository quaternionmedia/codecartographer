from .actions.collection import (
    col_clear,
    col_create,
    col_drop,
    col_alter,
    col_rename,
    col_schema,
)
from .actions.connection import (
    mongo_client,
    destory,
    databases,
    dbName,
)
from .actions.database import (
    db_create,
    db_drop,
    db_rename,
    db_watch,
)
from .actions.document import (
    doc_count,
    doc_clear_field,
    doc_insert,
    doc_remove,
    doc_select,
    doc_update,
)
from .actions.exceptions import (
    DBSyntaxError,
)

# from .actions.settings import *
from .actions.util import (
    get_uuid,
    hash_password,
)

from .models.base import (
    BaseCollection,
    BaseModel,
)
from .models.user import (
    User,
    UserCollection,
    user_auth,
    user_create,
    user_remove,
    user_select,
    user_schema,
    user_update,
)


# from .query import *
# from .schema import *
# from .table import *
# from .types import *
# from .utils import *


############### DEBUG ################
import logging
import pytest

log = logging.getLogger(__name__)
######################################

stream = None


@pytest.mark.asyncio
async def setup_codecarto_db():
    """Setup a database for codecarto.

    Returns
    -------
    database
        The codecarto database.
    """

    # create main database
    # db = await db_create("codecarto")
    db = await db_create("test_database")

    # create collections
    await col_create("users")

    # watch database
    # stream = await db_watch(db.name)

    # return database
    return db


# TODO: Should we be passing in a database object or a database name?
#       We know the name of the main database

# TODO: possible functions to implement
# Indexes:
#     Creating, reading, updating, and dropping indexes
#     can be important for performance. You might consider
#     functions like:
#         create_index()
#         list_indexes()
#         drop_index()

# Bulk Operations:
#     Sometimes, you might want to insert, update, or delete
#     many documents at once. This can be done more efficiently
#     with bulk operations. Consider:
#         bulk_insert()
#         bulk_update()
#         bulk_remove()

# Aggregation:
#     MongoDB offers powerful aggregation capabilities. Depending
#     on your needs, you might want to explore:
#         aggregate()

# Transactions:
#     For use cases that require atomicity for multiple operations,
#     you can use transactions in MongoDB. Consider:
#         start_transaction()
#         commit_transaction()
#         abort_transaction()

# Diagnostics and Management:
#     It's often useful to have some diagnostic or management functions:
#         get_server_status()
#         get_db_stats()
#         get_collection_stats()

# Replication and Sharding:
#     If you're dealing with a more advanced setup with replicas or
#     sharding, you might need specific functions for those. This is
#     more advanced and may not be required immediately.

# Cursors:
#     You may want to have more granular control over cursors,
#     especially if dealing with large datasets. Consider functions
#     to handle cursor iteration, timeouts, etc.

# GridFS:
#     If you're storing large files (like images, videos) in MongoDB,
#     you might use GridFS. You'd then need functions to handle this
#     feature.

# Error Handling:
#     Ensure that all your functions have proper error handling.
#     MongoDB can throw various errors (e.g., connection failures,
#     duplicate key errors), and you'll want to handle these gracefully.
