# accounts/models/login_log.py
from django.db import models


class LoginLog(models.Model):
    user = models.ForeignKey("accounts.TavUser", on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} @ {self.timestamp}"
