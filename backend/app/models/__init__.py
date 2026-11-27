from app.core.database import Base
from app.models.identity import Department, Role, Employee, AuthSession
from app.models.settings import SystemSetting, AuditLog
from app.models.leads import Lead, LeadSequence, LeadActivity, LeadActionLog
from app.models.inquiries import WebsiteInquiry, BuilderProject
from app.models.callbacks import (
    TblCallback,
    CallbackRescheduleLog,
    CallbackActivity,
)
from app.models.blogs import (
    TblBlog,
    TblBlogCategory,
    TblBlogAuthor,
    TblBlogTag,
    TblBlogComment,
)
from app.models.ai_agents import (
    AIAgentConfig,
    CustomerConsent,
    AIApprovalQueue,
    AIAgentExecutionLog,
    PropertyAlertHistory,
)

__all__ = [
    "Base",
    "Department",
    "Role",
    "Employee",
    "AuthSession",
    "SystemSetting",
    "AuditLog",
    "Lead",
    "LeadSequence",
    "LeadActivity",
    "LeadActionLog",
    "WebsiteInquiry",
    "BuilderProject",
    "TblCallback",
    "CallbackRescheduleLog",
    "CallbackActivity",
    "TblBlog",
    "TblBlogCategory",
    "TblBlogAuthor",
    "TblBlogTag",
    "TblBlogComment",
    "AIAgentConfig",
    "CustomerConsent",
    "AIApprovalQueue",
    "AIAgentExecutionLog",
    "PropertyAlertHistory",
]
