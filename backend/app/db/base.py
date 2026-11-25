"""Base database declaration importing all models to ensure complete metadata registration."""
from app.db.session import Base

# Import all models to register their tables in Base.metadata
import app.models.identity  # noqa: F401
import app.models.settings  # noqa: F401
import app.models.leads  # noqa: F401
import app.models.properties  # noqa: F401
import app.models.property_master  # noqa: F401
import app.models.inquiries  # noqa: F401
import app.models.property_verification  # noqa: F401
import app.models.owner_requests  # noqa: F401
import app.models.ai_agents  # noqa: F401

__all__ = ["Base"]
