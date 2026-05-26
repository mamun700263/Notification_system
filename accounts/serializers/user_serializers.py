from rest_framework import serializers
from accounts.models import TavUser, LoginLog, Account




class TavUserPublicSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = TavUser
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "is_verified",
            "account_status",
            "created_at",
        ]
        read_only_fields = fields


class TavUserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TavUser
        fields = [
            "first_name",
            "last_name",
            "phone",
        ]

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)
    
