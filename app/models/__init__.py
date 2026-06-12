"""ORM models package — imports all models so Alembic autogenerate can detect them."""
from app.models.attachment import Attachment  # noqa: F401
from app.models.bug import Bug  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.user import User  # noqa: F401
