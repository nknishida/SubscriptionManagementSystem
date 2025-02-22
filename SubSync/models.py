from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta  # For date calculations
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class User(AbstractUser):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)

    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

class Provider(models.Model):
    provider_name = models.CharField(max_length=255, unique=True)
    contact_email = models.EmailField(unique=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.provider_name

class Subscription(models.Model):
    CATEGORY_CHOICES = [
        ('software', 'Software'),
        ('billing', 'Billing'),
        ('server', 'Server'),
        ('domain', 'Domain'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('pending', 'Pending'),
        ('unpaid', 'Unpaid'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled'),
    ]

    subscription_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriber')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='subscription_provider')
    subscription_id =models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    billing_cycle = models.CharField(
        max_length=20, 
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('one-time', 'One-Time')
        ],
        default='monthly'
    )
    # renewal_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES)
    payment_method = models.CharField(
        max_length=50, 
        choices=[
            ('credit_card', 'Credit Card'),
            ('debit_card', 'Debit Card'),
            ('paypal', 'PayPal'),
            ('bank_transfer', 'Bank Transfer'),
            ('other', 'Other')
        ]
    )
    last_payment_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    auto_renewal = models.BooleanField(default=False)  # Checkbox for auto-renewal
    discount_coupon = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_subscriptions')
    
    updated_at = models.DateTimeField(auto_now=True)
    updated_by= models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_subscriptions')

    is_deleted = models.BooleanField(default=False)  # Soft delete flag
    deleted_at = models.DateTimeField(null=True, blank=True)  # Store delete time

    def soft_delete(self):
        """Soft delete: Hide subscription without affecting status."""
        self.is_deleted = True
        self.deleted_at = now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore subscription from soft delete."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def clean(self):
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError("End date cannot be earlier than the start date.")
        
    @property
    def renewal_date(self):
        if self.billing_cycle == 'monthly':
            return self.end_date + relativedelta(months=1)
        elif self.billing_cycle == 'quarterly':
            return self.end_date + relativedelta(months=3)
        elif self.billing_cycle == 'yearly':
            return self.end_date + relativedelta(years=1)
        return None  # For one-time payments