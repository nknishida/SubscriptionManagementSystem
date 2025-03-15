from datetime import timedelta
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
    # CATEGORY_CHOICES = [
    #     ('software', 'Software'),
    #     ('billing', 'Billing'),
    #     ('server', 'Server'),
    #     ('domain', 'Domain'),
    # ]
    # PAYMENT_STATUS_CHOICES = [
    #     ('paid', 'Paid'),
    #     ('pending', 'Pending'),
    #     ('unpaid', 'Unpaid'),
    # ]
    # STATUS_CHOICES = [
    #     ('active', 'Active'),
    #     ('expired', 'Expired'),
    #     ('canceled', 'Canceled'),
    # ]

    CATEGORY_CHOICES = ['Software', 'Billing', 'Server', 'Domain']
    PAYMENT_STATUS_CHOICES = ['Paid', 'Pending', 'Unpaid']
    STATUS_CHOICES = ['Active', 'Expired', 'Canceled']
    # subscription_category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    subscription_category = models.CharField(
        max_length=50, choices=[(c, c) for c in CATEGORY_CHOICES]
    )
    payment_status = models.CharField(
        max_length=20, choices=[(s, s) for s in PAYMENT_STATUS_CHOICES]
    )
    status = models.CharField(
        max_length=20, choices=[(s, s) for s in STATUS_CHOICES]
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriber')
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='subscription_provider')
    # subscription_id =models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    billing_cycle = models.CharField(
        max_length=20, 
    #     choices = [
    #     ('weekly', 'Weekly'),
    #     ('monthly', 'Monthly'),
    #     ('quarterly', 'Quarterly'),
    #     ('semi-annual', 'Semi-Annual'),
    #     ('annual', 'Annual'),
    #     ('biennial', 'Biennial'),
    #     ('triennial', 'Triennial'),
    #     ('one-time', 'One-Time'),
    # ],
        default='monthly'
    )
    # renewal_date = models.DateField()
    cost = models.DecimalField(max_digits=10, decimal_places=2)
    # payment_status = models.CharField(max_length=50, choices=PAYMENT_STATUS_CHOICES)
    payment_method = models.CharField(
        max_length=50, 
        # choices=[
        #     ('credit_card', 'Credit Card'),
        #     ('debit_card', 'Debit Card'),
        #     ('paypal', 'PayPal'),
        #     ('bank_transfer', 'Bank Transfer'),
        #     ('other', 'Other')
        # ]
    )
    last_payment_date = models.DateField(null=True, blank=True)
    next_payment_date = models.DateField(null=True, blank=True)
    # status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    auto_renewal = models.BooleanField(default=False)  # Checkbox for auto-renewal
    # discount_coupon = models.CharField(max_length=100, null=True, blank=True)

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
      
    def calculate_next_payment_date(self):
        """Calculate the next payment date based on !start_date //last_payment_date and billing_cycle."""
        if not self.start_date:
            print("Start date not set")
            return None

        cycle_mapping = {
            'weekly': relativedelta(weeks=1),
            'monthly': relativedelta(months=1),
            'quarterly': relativedelta(months=3),
            'semi-annual': relativedelta(months=6),
            'annual': relativedelta(years=1),
            'biennial': relativedelta(years=2),
            'triennial': relativedelta(years=3),
        }

        # last_payement_date = self.start_date?
        # next_payment_date = self.end_date?

        # If next_payment_date is not set, calculate it from !start_date//last_payment_date
        if not self.next_payment_date:
            self.next_payment_date = self.start_date + cycle_mapping.get(self.billing_cycle, relativedelta(days=0))
        else:
            # If next_payment_date is set, calculate the next payment date based on the billing cycle
            self.next_payment_date = self.next_payment_date + cycle_mapping.get(self.billing_cycle, relativedelta(days=0))

        print(f"Next Payment Date: {self.next_payment_date}")
        return self.next_payment_date

    def save(self, *args, **kwargs):
        """Override save method to calculate next_payment_date before saving."""
        if not self.next_payment_date:
            self.next_payment_date = self.calculate_next_payment_date()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subscription_category} - {self.billing_cycle}"

    
class SoftwareSubscriptions(models.Model):
    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='software_detail', unique=True)

    software_id =models.CharField()
    software_name = models.CharField(max_length=255)
    version = models.CharField(max_length=50, blank=True, null=True)
    # features = models.TextField(blank=True, null=True)
    # license_key = models.CharField(max_length=255)
    no_of_users = models.PositiveIntegerField(default=1)  # Ensures no negative users

    def __str__(self):
        return f"Software Details for {self.subscription.id}"
    
# BILLING_TYPE_CHOICES = [
#     ('Prepaid', 'Prepaid'),
#     ('Postpaid', 'Postpaid'),
# ]

# UTILITY_TYPE_CHOICES = {
#     'Prepaid': [('Internet', 'Internet'), ('Mobile', 'Mobile')],
#     'Postpaid': [('Electricity', 'Electricity'), ('Water', 'Water')],
# }

# def get_utility_type_choices():
#         return Utilities.UTILITY_TYPE_CHOICES.get('Prepaid', []) + Utilities.UTILITY_TYPE_CHOICES.get('Postpaid', [])

# class Utilities(models.Model):
#     subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name='billing', unique=True)

#     # BILLING_TYPE_CHOICES = [
#     #     ('Prepaid', 'Prepaid'),
#     #     ('Postpaid', 'Postpaid'),
#     # ]

#     # UTILITY_TYPE_CHOICES = {
#     #     'Prepaid': [('Internet', 'Internet'), ('Mobile', 'Mobile')],
#     #     'Postpaid': [('Electricity', 'Electricity'), ('Water', 'Water')],
#     # }

#     billing_type = models.CharField(max_length=50, choices=BILLING_TYPE_CHOICES)

#     utility_type = models.CharField(
#     max_length=50,
#     choices=get_utility_type_choices()  # Dynamically fetch choices
#     )

#     # utility_type = models.CharField(max_length=50)
#     location = models.CharField(max_length=50)
#     account_number = models.CharField(max_length=50, unique=True)  # Ensuring unique accounts

#     def clean(self):
#         """ Ensure subcategory matches the billing type. """
#         valid_choices = dict(self.UTILITY_TYPE_CHOICES).get(self.billing_type, [])
#         if self.utility_type not in [choice[0] for choice in valid_choices]:
#             raise ValidationError(f"Invalid utility type '{self.utility_type}' for billing type '{self.billing_type}'.")

#     def __str__(self):
#         return f"Billing for {self.subscription.subscription_category} - {self.billing_type} ({self.utility_type})"

from django.db import models
from django.core.exceptions import ValidationError

UTILITY_TYPE_CHOICES = [
    ('Prepaid', 'Prepaid'),
    ('Postpaid', 'Postpaid'),
]

# BILLING_TYPE_CHOICES= {
#     'Prepaid': [('Internet', 'Internet'), ('Mobile', 'Mobile')],
#     'Postpaid': [('Electricity', 'Electricity'), ('Water', 'Water')],
# }

# def get_utility_type_choices():
#     """Fetch choices dynamically from UTILITY_TYPE_CHOICES."""
#     return UTILITY_TYPE_CHOICES.get('Prepaid', []) + UTILITY_TYPE_CHOICES.get('Postpaid', [])

class Utilities(models.Model):
    subscription = models.OneToOneField('Subscription', on_delete=models.CASCADE, related_name='billing', unique=True)

    consumer_no =models.IntegerField()
    utility_name= models.CharField(max_length=255)
    utility_type = models.CharField(max_length=50, choices=UTILITY_TYPE_CHOICES)
    # billing_type = models.CharField(max_length=50, choices=get_utility_type_choices())  # Use function to set choices
    # location = models.CharField(max_length=50)
    # account_number = models.CharField(max_length=50, unique=True)

    # def clean(self):
    #     """ Ensure utility_type matches the selected billing_type. """
    #     valid_choices = UTILITY_TYPE_CHOICES.get(self.billing_type, [])
    #     if self.utility_type not in [choice[0] for choice in valid_choices]:
    #         raise ValidationError(f"Invalid utility type '{self.utility_type}' for billing type '{self.billing_type}'.")

    # def __str__(self):
    #     return f"Billing for {self.subscription.subscription_category} - {self.billing_type} ({self.utility_type})"

class Domain(models.Model):
    DOMAIN_TYPE_CHOICES = [
        ('.com', '.com'),
        ('.in', '.in'),
    ]

    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="domain", unique=True)

    domain_id =models.IntegerField()
    domain_name = models.CharField(max_length=255, unique=True, help_text="Fully Qualified Domain Name (FQDN)")
    domain_type = models.CharField(max_length=255,
                                    # choices=DOMAIN_TYPE_CHOICES
                                    )
    
    ssl_certification = models.BooleanField(default=False, help_text="Indicates if SSL is enabled for the domain")
    ssl_expiry_date = models.DateField(blank=True, null=True, help_text="SSL certificate expiration date")
    whois_protection = models.BooleanField(default=False, help_text="WHOIS privacy protection enabled or not")
    name_servers = models.CharField(max_length=255)
    hosting_provider = models.CharField(max_length=255)
    
    # domain_transfer_status = models.CharField(
    #     max_length=50,
    #     choices=[
    #         ('locked', 'Locked'),
    #         ('unlocked', 'Unlocked'),
    #         ('pending_transfer', 'Pending Transfer'),
    #     ],
    #     default='locked',
    #     help_text="Current status of domain transfer"
    # )

    def __str__(self):
        return self.domain_name


class Servers(models.Model):
    SERVER_TYPE_CHOICES = [
        ('In-house', 'In-house'),
        ('External', 'External'),
    ]

    subscription = models.OneToOneField(Subscription, on_delete=models.CASCADE, related_name="server", unique=True)
    
    server_name = models.CharField(max_length=255)
    server_type = models.CharField(max_length=50, choices=SERVER_TYPE_CHOICES)
    # server_capacity = models.PositiveIntegerField(default=0, help_text="Total resource capacity (e.g., CPU, RAM, storage).")
    server_capacity= models.CharField(max_length=255)

    def __str__(self):
        return self.server_name

class Hardware(models.Model):

    TYPE_CHOICES = [
        ('Laptop', 'Laptop'),
        ('Desktop', 'Desktop'),
        ('Mobile Phone', 'Mobile Phone'),
        ('Tablet', 'Tablet'),
        ('Network Device', 'Network Device'),
        ('Air Conditioner', 'Air Conditioner'),
        ('Server', 'Server'),
        ('Printer', 'Printer'),
        ('Scanner', 'Scanner'),
        ('Other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance')
    ]

    # hardware_name = models.CharField(max_length=100)
    hardware_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    manufacturer = models.CharField(max_length=255)
    model_number = models.CharField(max_length=255)
    serial_number = models.CharField(max_length=100, unique=True)
    assigned_department = models.CharField(max_length=255)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hardware')

    def __str__(self):
        return f"{self.hardware_name} ({self.serial_number})"

    class Meta:
        db_table = 'hardware'

class Warranty(models.Model):
    EXTENDED_WARRANTY_PERIODS = [
        (1, '1 Year'),
        (2, '2 Years'),
        (3, '3 Years'),
        (5, '5 Years'),
    ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='warranty')
    warranty_expiry_date = models.DateField()
    is_extended_warranty = models.BooleanField(default=False)
    extended_warranty_period = models.IntegerField(choices=EXTENDED_WARRANTY_PERIODS, null=True, blank=True)

    def __str__(self):
        return f"Warranty for {self.hardware} expires on {self.warranty_expiry_date}"

class Purchase(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='purchase')
    purchase_date = models.DateField()
    purchase_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"Purchase for {self.hardware} on {self.purchase_date}"

class HardwareService(models.Model):
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE, related_name='services')
    last_service_date = models.DateField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    free_service_until = models.DateField(null=True, blank=True)
    service_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    service_provider = models.CharField(max_length=100, null=True, blank=True)
    service_notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Service for {self.hardware} on {self.last_service_date}"

class Computer(models.Model):
    COMPUTER_TYPES = [
        ('Laptop', 'Laptop'),
        ('Desktop', 'Desktop'),
    ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='computer')
    computer_type = models.CharField(max_length=50, choices=COMPUTER_TYPES)
    cpu = models.CharField(max_length=100)
    ram = models.CharField(max_length=100)
    storage = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.computer_type}: {self.hardware}"
    
class PortableDevice(models.Model):
    PORTABLE_DEVICE_TYPES = [
        ('Mobile Phone', 'Mobile Phone'),
        ('Tablet', 'Tablet'),
    ]

    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='portable_device')
    device_type = models.CharField(max_length=50, choices=PORTABLE_DEVICE_TYPES)
    os_version = models.CharField(max_length=100)
    storage = models.CharField(max_length=100)
    imei_number = models.CharField(max_length=100, null=True, blank=True)  # Only for Mobile Phone

    def __str__(self):
        return f"{self.device_type}: {self.hardware}"

class NetworkDevice(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='network_device')
    throughput = models.CharField(max_length=100)
    ip_address = models.CharField(max_length=100)

    def __str__(self):
        return f"Network Device: {self.hardware}"
    
class AirConditioner(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='air_conditioner')
    btu_rating = models.CharField(max_length=100)
    energy_rating = models.CharField(max_length=100)

    def __str__(self):
        return f"Air Conditioner: {self.hardware}"
    
class HardwareServers(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='server')
    cpu = models.CharField(max_length=100)
    ram = models.CharField(max_length=100)
    storage_configuration = models.CharField(max_length=100)
    operating_system = models.CharField(max_length=100)

    def __str__(self):
        return f"Server: {self.hardware}"
    
class Printer(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='printer')
    print_technology = models.CharField(max_length=100)
    print_speed = models.CharField(max_length=100)
    connectivity = models.CharField(max_length=100)

    def __str__(self):
        return f"Printer: {self.hardware}"
    
class Scanner(models.Model):
    hardware = models.OneToOneField(Hardware, on_delete=models.CASCADE, related_name='scanner')
    scan_resolution = models.CharField(max_length=100)
    scan_type = models.CharField(max_length=100)
    connectivity = models.CharField(max_length=100)

    def __str__(self):
        return f"Scanner: {self.hardware}"
    

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from calendar import monthrange
import logging
logger = logging.getLogger(__name__)

class Reminder(models.Model):
    REMINDER_TYPE_CHOICES = [
        ('renewal', 'Renewal'),
        ('maintenance', 'Maintenance'),
        ('over due', 'Over Due'),
        ('server break down', 'Server Break Down'),
        ('custom', 'Custom'),
    ]
    REMINDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
    ]
    NOTIFICATION_METHOD_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('in-app', 'In-App'),
        ('all', 'All'),
    ]
    SUBSCRIPTION_CYCLE_CHOICES = [
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi-annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('biennial', 'Biennial'),
        ('triennial', 'Triennial'),
    ]

    subscription_cycle = models.CharField(
        max_length=20, choices=SUBSCRIPTION_CYCLE_CHOICES, default='monthly',
        help_text="Defines the frequency of the subscription."
    )
    reminder_days_before = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)],
        help_text="For weekly/monthly cycles: How many days before to receive a reminder?"
    )
    reminder_months_before = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)],
        help_text="For long-term cycles: How many months before to receive a reminder?"
    )
    reminder_day_of_month = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="For long-term cycles: Specific day of the month for reminder."
    )
    optional_days_before = models.IntegerField(
        blank=True, null=True, validators=[MinValueValidator(1)],
        help_text="Optional: Extra days before the reminder."
    )
    reminder_status = models.CharField(
        max_length=20, choices=REMINDER_STATUS_CHOICES, default='pending'
    )
    notification_method = models.CharField(
        max_length=20, choices=NOTIFICATION_METHOD_CHOICES, default='email',
        help_text="Method of notification (email, SMS, etc.)"
    )
    recipients = models.TextField(
        blank=True, null=True, help_text="Comma-separated email addresses."
    )
    custom_message = models.TextField(
        blank=True, null=True, help_text="Custom message for the reminder."
    )
    reminder_date = models.DateField(blank=True, null=True, help_text="Next reminder date.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reminder_type = models.CharField(max_length=50, choices=REMINDER_TYPE_CHOICES, default='renewal')
    # reminder_time = models.TimeField(
                                    # default="09:00:00"
                                    # default="15:15:00",
                                    #  help_text="Time to send the reminder.")

    def get_valid_day(self, year, month, day):
        """Helper method to get a valid day of the month."""
        _, last_day = monthrange(year, month)
        return min(day, last_day)

    def calculate_all_reminder_dates(self, subscription):
        """Calculate all reminder dates for a subscription."""
        if not subscription.next_payment_date:
            logger.error("No next_payment_date found for subscription")
            return []

        today = timezone.now().date()
        reminder_dates = []

        # For weekly/monthly cycles
        if self.subscription_cycle in ['weekly', 'monthly']:
            if self.reminder_days_before:
                start_date = subscription.next_payment_date - timedelta(days=int(self.reminder_days_before))
                current_date = start_date
                while current_date < subscription.next_payment_date:
                    if current_date >= today:
                        reminder_dates.append(current_date)
                    current_date += timedelta(days=1)

        # For long-term cycles
        elif self.subscription_cycle in ['quarterly', 'semi-annual', 'annual', 'biennial', 'triennial']:
            if self.reminder_months_before and self.reminder_day_of_month:
                start_date = max(
                    subscription.next_payment_date - relativedelta(months=self.reminder_months_before),
                    today
                )
                start_date = start_date.replace(
                    day=self.get_valid_day(start_date.year, start_date.month, self.reminder_day_of_month)
                )
                current_date = start_date
                while current_date < subscription.next_payment_date:
                    if current_date >= today:
                        reminder_dates.append(current_date)
                    current_date += relativedelta(months=1)

        # Add optional_days_before reminder if present
        if self.optional_days_before:
            optional_reminder_date = subscription.next_payment_date - timedelta(days=self.optional_days_before)
            current_date = optional_reminder_date
            while current_date < subscription.next_payment_date:
                if optional_reminder_date >= today:
                    reminder_dates.append(optional_reminder_date)
                current_date += timedelta(days=1)

        logger.info(f"Generated Reminder Dates: {reminder_dates}")
        return reminder_dates

    def __str__(self):
        return f"Reminder for {self.subscription_cycle} cycle - {self.reminder_status}"
    

# Separate Linking Tables
class ReminderSubscription(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='subscription_reminder')
    subscription = models.ForeignKey('Subscription', on_delete=models.CASCADE)

class ReminderHardware(models.Model):
    reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='hardware_reminder')
    hardware = models.ForeignKey('Hardware', on_delete=models.CASCADE)

# class ReminderCustomer(models.Model):
#     reminder = models.ForeignKey(Reminder, on_delete=models.CASCADE, related_name='customer_reminder')
#     customer = models.ForeignKey('Customer', on_delete=models.CASCADE)

class Customer(models.Model):
    # STATUS_CHOICES = [
    #     ('active', 'Active'),
    #     ('inactive', 'Inactive'),
    #     # ('pending', 'Pending')
    # ]
    STATUS_CHOICES = ['Active', 'Inactive']

    CUSTOMER_TYPE_CHOICES = [
        ('inhouse', 'In-house'),
        ('external', 'External'),
    ]
    
    customer_name = models.CharField(max_length=100)
    contact_phone = models.CharField(max_length=20)
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=[(s, s) for s in STATUS_CHOICES])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    customer_type = models.CharField(max_length=50, choices=CUSTOMER_TYPE_CHOICES)

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')

    # resources = models.ManyToManyField(Resource, through='CustomerResource', related_name='customers')

    def __str__(self):
        return self.customer_name

    class Meta:
        db_table = 'customer'
        ordering = ['-created_at']

class Resource(models.Model):

    RESOURCE_TYPE_CHOICES = [
        ('database', 'Database'),
        ('compute', 'Compute'),
        ('storage', 'Storage'),
        ('network', 'Network'),
        ('website', 'Website')
    ]
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_use', 'In Use'),
        ('maintenance', 'Maintenance')
    ]
    
    resource_name = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=50, choices=RESOURCE_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    capacity = models.CharField(
        max_length=100,
        help_text="Specify resource capacity (e.g., 4 vCPUs, 100 GB, 1 TB bandwidth)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    server= models.ForeignKey(Servers, on_delete=models.CASCADE, related_name='server_resources')
    
    user= models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_resources')
    customers = models.ManyToManyField(Customer, through='CustomerResource', related_name='customer_resources')

    def __str__(self):
        return self.resource_name

    class Meta:
        db_table = 'resource'

class CustomerResource(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('unpaid', 'Unpaid'),
        ('pending', 'Pending'),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='customer')
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE, related_name='resources')

    total_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Total cost of the resource usage.")
    usage_start_date = models.DateTimeField(help_text="Start date of resource usage.")
    usage_end_date = models.DateTimeField(help_text="End date of resource usage.")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')