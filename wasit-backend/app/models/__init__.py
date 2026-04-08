from app.core.database import Base
from app.models.institution import Class, Filiere, School
from app.models.notification import Notification
from app.models.problem import AggregationGroup, Problem
from app.models.student import ProjectGroup, ProjectGroupMember, Student
from app.models.ticket import Ticket, TicketHistory
from app.models.telegram import TelegramGroup, TelegramMessage
from app.models.user import Role, User

__all__ = [
    "Base",
    "Role",
    "User",
    "School",
    "Filiere",
    "Class",
    "Student",
    "ProjectGroup",
    "ProjectGroupMember",
    "Ticket",
    "TicketHistory",
    "Problem",
    "AggregationGroup",
    "Notification",
    "TelegramGroup",
    "TelegramMessage",
]
