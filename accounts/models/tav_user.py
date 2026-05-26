"""
TavUser model.

Features:
- email as primary identifier (unique, indexed)
- first_name / last_name, full_name property
- phone with regex validator (store normalized externally)
- roles (TextChoices)
- soft-delete (is_deleted + deleted_at)
- failed login tracking and last failed timestamp
- audit fields (signup/login IP + user agent, created/updated)
- social/provider fields (auth_provider, provider_id, provider_picture, provider_raw_payload)
- tenant support (tenant_id UUID)
- handy instance helpers (mark_verified, soft_delete, restore, increment_failed_login, reset_failed_logins)
- DB indexes / unique constraints for performance and safety
- Compatible with dj-rest-auth / allauth / SimpleJWT flows
"""
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from accounts.usermanagers import TavUserManager
from .enums import AccountStatus
    # Account state & lifecycle

    

class TavUser(AbstractUser):
    # Remove username (we use email)
    username = None

    # Core identity
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    first_name = models.CharField(_("first name"), max_length=100, blank=True)
    last_name = models.CharField(_("last name"), max_length=100, blank=True)

    # Contact
    phone = models.CharField(
        _("phone"),
        max_length=20,
        blank=True,
        null=True,
        validators=[RegexValidator(regex=r"^\+?\d{7,15}$")],
        help_text=_("E.164-ish phone; normalize before saving if necessary."),
    )

    # Verification / provider / signup metadata
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    verification_method = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text=_("How the user was verified: email/google/github/linkedin/admin"),
    )

    # Provider / social auth support
    signup_method = models.CharField(
        max_length=30,
        default="local",
        help_text=_("local, google, github, linkedin, etc."),
    )
    auth_provider = models.CharField(
        max_length=30,
        blank=True,
        null=True,
        help_text=_("OAuth provider that issued identity"),
    )
    provider_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True,
        help_text=_("Provider's subject id (sub) or uid"),
    )
    provider_picture = models.URLField(blank=True, null=True)
    provider_raw_payload = models.JSONField(blank=True, null=True, editable=False)



    account_status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.PENDING,
        db_index=True,
    )
    account_locked_until = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    # Security tracking
    failed_login_attempts = models.PositiveIntegerField(default=0)
    last_failed_login_at = models.DateTimeField(blank=True, null=True)
    last_password_reset_at = models.DateTimeField(blank=True, null=True)

    # Audit / telemetry
    signup_ip = models.GenericIPAddressField(blank=True, null=True)
    signup_user_agent = models.TextField(blank=True, null=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_login_user_agent = models.TextField(blank=True, null=True)

    # Multi-tenant / org support
    # tenant_id = models.UUIDField(blank=True, null=True, db_index=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft-delete helper boolean (derivable from account_status but convenient)
    is_deleted = models.BooleanField(default=False, db_index=True)

    # Django auth settings
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    # Manager will be provided separately
    objects = TavUserManager()# replace with your TavUserManager in accounts.usermanagers

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["provider_id", "auth_provider"]),
            # models.Index(fields=["tenant_id"]),
            models.Index(fields=["account_status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["provider_id", "auth_provider"],
                name="unique_provider_per_user",
                condition=~models.Q(provider_id=None) & ~models.Q(auth_provider=None),
            )
        ]
        swappable = "AUTH_USER_MODEL"

    # -------------------------
    # Properties & helpers
    # -------------------------
    @property
    def full_name(self) -> str:
        parts = [p for p in (self.first_name, self.last_name) if p]
        return " ".join(parts) if parts else self.email

    def __str__(self) -> str:
        return f"{self.full_name} <{self.email}>"

    # -------------------------
    # Instance mutation helpers
    # -------------------------
    def mark_verified(self, method: str = "email"):
        """Mark user verified and record timestamp + method."""
        self.is_verified = True
        self.verified_at = timezone.now()
        self.verification_method = method
        if self.account_status == self.AccountStatus.PENDING:
            self.account_status = self.AccountStatus.ACTIVE
        self.save(update_fields=["is_verified", "verified_at", "verification_method", "account_status"])

    def soft_delete(self, by=None):
        """Soft-delete the user."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.account_status = self.AccountStatus.DELETED
        self.save(update_fields=["is_deleted", "deleted_at", "account_status"])

    def restore(self):
        """Restore a soft-deleted user (admin action)."""
        self.is_deleted = False
        self.deleted_at = None
        self.account_status = self.AccountStatus.ACTIVE
        self.save(update_fields=["is_deleted", "deleted_at", "account_status"])

    def increment_failed_login(self):
        """Increase failed count and set last failed timestamp."""
        self.failed_login_attempts = models.F('failed_login_attempts') + 1
        self.last_failed_login_at = timezone.now()
        self.save(update_fields=["failed_login_attempts", "last_failed_login_at"])
        # Refresh from db to get the integer value (F-expression)
        self.refresh_from_db(fields=["failed_login_attempts", "last_failed_login_at"])

    def reset_failed_logins(self):
        """Reset the failed login counter (call on successful auth)."""
        self.failed_login_attempts = 0
        self.last_failed_login_at = None
        self.save(update_fields=["failed_login_attempts", "last_failed_login_at"])

    def lock_account_until(self, until: timezone.datetime):
        """Lock account until a specific datetime."""
        self.account_locked_until = until
        self.account_status = self.AccountStatus.LOCKED
        self.save(update_fields=["account_locked_until", "account_status"])

    def unlock_account(self):
        self.account_locked_until = None
        if self.account_status == self.AccountStatus.LOCKED:
            self.account_status = self.AccountStatus.ACTIVE
        self.save(update_fields=["account_locked_until", "account_status"])
