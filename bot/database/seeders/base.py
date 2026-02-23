"""Base class for database seeders."""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class BaseSeeder(ABC):
    """Base class for all database seeders."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def seed(self) -> None:
        """Execute the seeding logic."""
        pass

    async def check_exists(self, model_class, **filters) -> bool:
        """Check if a record already exists."""
        from sqlalchemy import select
        result = await self.session.execute(
            select(model_class).filter_by(**filters)
        )
        return result.scalar_one_or_none() is not None
