from common.validators.user_validators import validate_not_future_date
from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date, timedelta


class TestValidators(TestCase):
    def test_valid_date_today(self):
        try:
            validate_not_future_date(date.today())
        except ValidationError:
            self.fail("ValidationError raised for today's date")

    def test_valid_past_date(self):
        try:
            validate_not_future_date(date.today() - timedelta(days=5))
        except ValidationError:
            self.fail("ValidationError raised for past date")

    def test_invalid_future_date(self):
        future_date = date.today() + timedelta(days=5)
        with self.assertRaises(ValidationError):
            validate_not_future_date(future_date)
