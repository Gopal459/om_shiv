"""Repositories pattern layer encapsulating data access and queries."""
from app.repositories.base import BaseRepository
from app.repositories.staff_repository import staff_repo, StaffRepository
from app.repositories.role_repository import role_repo, RoleRepository
from app.repositories.department_repository import department_repo, DepartmentRepository
from app.repositories.lead_repository import lead_repo, LeadRepository
from app.repositories.property_repository import property_repo, PropertyRepository
from app.repositories.master_repository import master_repo, MasterRepository
from app.repositories.setting_repository import setting_repo, SettingRepository

__all__ = [
    "BaseRepository",
    "staff_repo",
    "StaffRepository",
    "role_repo",
    "RoleRepository",
    "department_repo",
    "DepartmentRepository",
    "lead_repo",
    "LeadRepository",
    "property_repo",
    "PropertyRepository",
    "master_repo",
    "MasterRepository",
    "setting_repo",
    "SettingRepository",
]
