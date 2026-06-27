import logging

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pricemonitorbot.config import settings

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    jobstore = SQLAlchemyJobStore(url=settings.DATABASE_URL.replace("+asyncpg", ""))
    jobstores = {"default": jobstore}

    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone=settings.SCHEDULER_TIMEZONE,
    )

    return scheduler
