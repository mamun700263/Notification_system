import re
from rest_framework import serializers
from accounts.models import TavUser, LoginLog, Account
from rest_framework.exceptions import ValidationError


class TavUserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = TavUser
        fields = [
            "email",
            "password",
            # "first_name",
            # "last_name",
        ]
    def strong_pass_check(self,password):
        if len(password) < 8:
            return False

        upper_case = any(c.isupper() for c in password)
        lower_case = any(c.islower() for c in password)
        number = any(c.isdigit() for c in password)
        special_char = bool(re.search(r"[!@#$%^&*(),.?\":{}|<>]", password))

        return upper_case and lower_case and number and special_char

    def create(self, validated_data):
        password = validated_data.pop("password")

        if not self.strong_pass_check(password):
            raise ValidationError(
                {
                    "password": (
                        "Password must contain uppercase, lowercase, "
                        "number, and special character (min 8 chars)."
                    )
                }
            )

        user = TavUser.objects.create_user(
            password=password,
            **validated_data
        )
        return user
    
class LoginLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginLog
        fields = [
            "id",
            "user",
            "ip_address",
            "user_agent",
            "timestamp",
        ]
        read_only_fields = fields

from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from accounts.models import TavUser


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # optional custom claims
        token["email"] = user.email
        token["role"] = getattr(user, "role", None)

        return token