"""PostgreSQL native enums: persist StrEnum `.value`, not member `.name` (SQLAlchemy default for PEP enums)."""

from enum import Enum
from typing import TypeVar

from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

T = TypeVar("T", bound=Enum)


def pg_str_enum(enum_class: type[T], postgres_type_name: str) -> PG_ENUM:
    """Bind/write labels that already exist on the server (Alembic `name=`)."""
    return PG_ENUM(
        enum_class,
        name=postgres_type_name,
        values_callable=lambda cls: [m.value for m in cls],
        create_type=False,
    )
