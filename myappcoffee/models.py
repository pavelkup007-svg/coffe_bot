from django.db import models
from django.utils import timezone
from decimal import Decimal

class User(models.Model):
    user_id = models.PositiveIntegerField(unique=True)
    username = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, blank=True)
    password = models.CharField(max_length=255, blank=True)
    cups = models.PositiveIntegerField(default=0)
    cups_new = models.PositiveIntegerField(default=0)
    last_cup_date = models.DateField(null=True, blank=True)
    cups_today = models.PositiveIntegerField(default=0)
    deposit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), editable=True)
    historical_amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    registration_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.username} {self.user_id}'

    def update_cups_today(self):
        today = timezone.now().date()
        if self.last_cup_date != today:
            self.cups_today = 0
            self.last_cup_date = today
        self.cups_today += 1
        self.cups += 1
        self.cups_new += 1
        self.save()

    def save(self, *args, **kwargs):
        # Преобразование цены к Decimal
        cup_price = Decimal('1.00')
        # Расчет суммы к оплате
        self.amount_due = self.historical_amount_due + (self.cups_new * cup_price)
        super().save(*args, **kwargs)
