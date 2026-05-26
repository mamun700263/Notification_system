
from rest_framework import serializers
from accounts.models import TavUser, LoginLog, Account



class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "date_of_birth",
            "bio",
            "mobile",
            "profile_picture",
        ]


