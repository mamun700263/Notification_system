from django.db import models
class AccountStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DISABLED = "disabled", "Disabled"
    LOCKED = "locked", "Locked"
    PENDING = "pending", "Pending Verification"
    DELETED = "deleted", "Deleted"

