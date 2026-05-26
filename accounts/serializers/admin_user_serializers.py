

from rest_framework import serializers
from accounts.models import TavUser, LoginLog, Account


class TavUserAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = TavUser
        fields = "__all__"
        read_only_fields = [
            "password",
        ]
