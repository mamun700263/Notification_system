from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from accounts.models.enums import AccountStatus


class TavUserManager(BaseUserManager):

    use_in_migrations = True

    # ---------------------------------------
    # Internal creation helper
    # ---------------------------------------
    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email is required.")

        email = self.normalize_email(email)

        # Validate password only if provided (social auth may skip)
        if password:
            validate_password(password)

        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            # Unusable password for social-auth accounts
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    # ---------------------------------------
    # Public: create_user
    # ---------------------------------------
    @transaction.atomic
    def create_user(
        self,
        email,
        password=None,
        first_name="",
        last_name="",
        role=None,
        signup_method="local",
        # tenant_id=None,
        **extra_fields
    ):
        # Default role if not provided
        # role = role or self.model.Roles.CLIENT

        # Safe defaults for new user
        extra_fields.setdefault("first_name", first_name)
        extra_fields.setdefault("last_name", last_name)
        # extra_fields.setdefault("role", role)
        extra_fields.setdefault("signup_method", signup_method)
        # extra_fields.setdefault("tenant_id", tenant_id)

        # Account lifecycle defaults
        extra_fields.setdefault("account_status", AccountStatus.PENDING)
        extra_fields.setdefault("is_verified", False)
        extra_fields.setdefault("failed_login_attempts", 0)

        return self._create_user(email=email, password=password, **extra_fields)

    # ---------------------------------------
    # Public: create_superuser
    # ---------------------------------------
    @transaction.atomic
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", self.model.Roles.ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("verified_at", timezone.now())
        extra_fields.setdefault("verification_method", "superuser")

        # Hard safety checks
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email=email, password=password, **extra_fields)

    # ---------------------------------------
    # Social / provider-based creation
    # ---------------------------------------
    @transaction.atomic
    def create_user_from_provider(
        self,
        provider,
        provider_id,
        email,
        first_name="",
        last_name="",
        provider_picture=None,
        provider_raw_payload=None,
        # tenant_id=None,
        **extra_fields
    ):
        """
        Used for Google / GitHub / LinkedIn login.
        Creates verified user with unusable password.
        """
        extra_fields.setdefault("auth_provider", provider)
        extra_fields.setdefault("provider_id", provider_id)
        extra_fields.setdefault("provider_picture", provider_picture)
        extra_fields.setdefault("provider_raw_payload", provider_raw_payload)
        extra_fields.setdefault("signup_method", provider)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("verified_at", timezone.now())
        extra_fields.setdefault("verification_method", provider)
        extra_fields.setdefault("account_status", AccountStatus.ACTIVE)
        # extra_fields.setdefault("role", self.model.Roles.CLIENT)
        # extra_fields.setdefault("tenant_id", tenant_id)

        return self._create_user(
            email=email,
            password=None,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )
