from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
import secrets


class Permission(models.Model):
    code = models.CharField(max_length=128, unique=True, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.code


class UserManager(BaseUserManager):
    def create_user(self, username, **extra_fields):
        if not username:
            raise ValueError("username is required")
        user = self.model(username=username, **extra_fields)
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, username, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, **extra_fields)


class Role(models.TextChoices):
    PRODUCER = "producer", "Producer"
    VIEWER = "viewer", "Viewer"
    ADMIN = "admin", "Admin"


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=128, unique=True)
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.PRODUCER)

    extra_permissions = models.ManyToManyField(
        "accounts.Permission",
        blank=True,
        related_name="users_with_extra",
    )
    revoked_permissions = models.ManyToManyField(
        "accounts.Permission",
        blank=True,
        related_name="users_with_revoked",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def has_api_permission(self, code: str) -> bool:
        """
        Permission evaluation order;
        1) role default permissions from JSON
        2) extra_permissions (DB)
        3) revoked_permissions (DB)
        4) '*' in role policy grants all - unless explicitly revoked.
        """
        from apps.common.policy_loader import load_permission_policy
        if not self.is_active:
            return False

        policy = load_permission_policy()
        role_perms = set(policy.get("roles", {}).get(self.role, []))

        revoked = set(self.revoked_permissions.values_list("code", flat=True))

        if "*" in role_perms:
            return code not in revoked

        extras = set(self.extra_permissions.values_list("code", flat=True))

        effective = (role_perms | extras) - revoked
        return code in effective


class APIKey(models.Model):
    key = models.CharField(max_length=64, unique=True, db_index=True)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="api_keys")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @classmethod
    def generate(cls, user):
        return cls.objects.create(
            user=user,
            key=secrets.token_hex(32),
        )

    def __str__(self):
        return f"{self.user.username}:{self.key[:3]}***"
