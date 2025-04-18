import os
import re
import random
import string
import calendar
import logging
from datetime import date, timedelta, datetime
from collections import defaultdict
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db import models
from django.db.models import (
    Q, F, Sum, Count, ExpressionWrapper, DurationField,
    DateField, IntegerField
)
from django.db.models.functions import (
    ExtractYear, ExtractMonth, TruncMonth
)
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timezone import now
from django.utils.dateparse import parse_date
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth.password_validation import validate_password
from django.views.decorators.csrf import csrf_exempt

from rest_framework import (
    generics, status, permissions, filters
)
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from django_filters.rest_framework import DjangoFilterBackend

import SubSync

from .models import (
    Subscription, Provider, ReminderSubscription, SoftwareSubscriptions, Utilities,
    Domain, Servers, Resource, Customer, Notification, Purchase, HardwareService,
    Warranty, Hardware, Reminder, Computer, ReminderCustomer, ReminderHardware
)
from .serializers import (
    SubscriptionSerializer, ComputerSerializer, CustomerSerializer,
    HardwareSerializer, OnPremServerUsageSerializer, PasswordResetSerializer,
    ResourceAddSerializer, ResourceViewSerializer, ServerUsageSerializer,
    SubscriptionDetailSerializer, SubscriptionHistorySerializer,
    SubscriptionUpdateSerializer, SubscriptionWarningSerializer,
    UserSerializer, NotificationSerializer, UserStatusUpdateSerializer,
    ProviderSerializer, ResourceNameSerializer, ReminderSerializer,
    UserProfileSerializer, ServerSerializer
)

# Setup logger
logger = logging.getLogger(__name__)

from django.contrib.auth import get_user_model
User = get_user_model()

class LoginAPIView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        print("Request data:", request.data)  # Debug print
        email = request.data.get('email')
        print("emial:",email)
        password = request.data.get('password')
        print("password:",password)
        
        user = authenticate(email=email, password=password)  #  Use Django's auth system

        if user is None:
            return Response({
                'message': 'Invalid email or password.',
                'status': status.HTTP_401_UNAUTHORIZED
                ,'error': 'Invalid email or password'
                },
                  status=status.HTTP_401_UNAUTHORIZED)
        
         # Check if user is active
        if not user.is_active:
            return Response({
                'message': 'Account is inactive. Please contact administrator.',
                'status': status.HTTP_403_FORBIDDEN,
                'error': 'Account inactive'
            }, status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful',
            'username': user.username, 
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'status': status.HTTP_200_OK,
        }, status=status.HTTP_200_OK)


class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        print("email:",email)

        if not email:
            return Response({"message": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Always return a generic message to avoid email enumeration
            return Response({
                "message": "The email address you entered isn't registered with us. Please check for typos or use a different email address.","status":status.HTTP_200_OK
            }, status=status.HTTP_200_OK)
        
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        frontend_url = os.getenv('FRONTEND_URL')
        reset_url = f"{frontend_url}/reset-password/{uidb64}/{token}"

        subject = "Password Reset Request"
        message = (
            f"Hi {user.username},\n\n"
            "We received a request to reset your password. Click the link below to set a new password:\n"
            f"{reset_url}\n\n"
            "If you didn't request this, please ignore this email.\n"
            "Thank you."
        )
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        except Exception as e:
            print(f"Error sending email: {e}")
            return Response(
                {
                    "message": "Failed to send password reset email. Please try again later.",
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            "message": "If this email is registered with us, you'll receive a password reset link shortly. Please check your inbox.",
            'status': status.HTTP_200_OK,
        }, status=status.HTTP_200_OK)


class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            uidb64 = serializer.validated_data.get('uid')
            token = serializer.validated_data.get('token')
            new_password = serializer.validated_data.get('new_password')

            print(request.data)
            
            try:
                uid = force_str(urlsafe_base64_decode(uidb64))
                print("uid:",uid)
                user = User.objects.get(pk=uid)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response({"message": "Invalid uid."}, status=status.HTTP_400_BAD_REQUEST)
            
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                return Response({"message": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password reset successful",
                             'status': status.HTTP_200_OK,}, status=status.HTTP_200_OK)
        
        else:
            print("Reset Password Error:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]  # Only logged-in users can change their password

    def post(self, request):
        logger.info(f"Request data: {request.data}")

        user = request.user  # Get the currently logged-in user
        old_password = request.data.get("currentPassword")
        new_password = request.data.get("newPassword")
        print(f"current password:{old_password} , new password:{new_password}")
        logger.info("Starting password validation checks...")

        if not old_password or not new_password:
            logger.info("Missing required fields in password change request")
            logger.info(f"Received fields: {list(request.data.keys())}")
            return Response(
                {"error": "Both old_password and new_password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if old password is correct
        if not user.check_password(old_password):
            logger.info(f"Invalid old password provided for user {user.username}")
            return Response({"message": "Old password is incorrect",'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password (checks Django password validators)
        try:
            logger.info("Validating new password complexity...")
            validate_password(new_password, user)
            logger.info("New password meets complexity requirements")
        except ValidationError as e:
            # error_messages = {
            #     'The password is too similar to the username.': 'Password should not contain your username',
            #     'This password is too short.': 'Password must be at least 8 characters',
            #     'This password is too common.': 'Password is too common',
            #     'This password is entirely numeric.': 'Password cannot be all numbers'
            # }
            
            # formatted_errors = []
            # for error in e.messages:
            #     formatted_errors.append(error_messages.get(error, error))
            
            logger.info(f"Password validation failed for user {user.username}: {e.messages}")
            
            return Response({"message": e.messages,'status':status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

        # Update password
        try:
            logger.info("Attempting to set new password...")
            user.set_password(new_password)
            user.save()
            logger.info(f"Password successfully changed for user {user.username}")
            return Response({"message": "Password updated successfully",'status': status.HTTP_200_OK,}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.info(f"Error changing password for user {user.username}: {str(e)}")
            return Response(
                {"error": "An unexpected error occurred while changing password"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class CreateUserAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def generate_random_password(self, length=12):
        """Generate a random password with letters, digits, and special characters"""
        characters = string.ascii_letters + string.digits + string.punctuation
        return ''.join(random.choices(characters, k=length))

    def post(self, request):
        print(request.data)
        email = request.data.get("email")
        username = request.data.get("name")
        role = request.data.get("role")
        phone_number = request.data.get("phoneNumber")

        if not email or not username or not role:
            return Response({"message": "Username, role, and email are required","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({"message": "Email already exists","status": status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            with transaction.atomic():

                if User.objects.filter(email=email).exists():
                    return Response({"message": "Email already exists","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

                # Generate a random password
                random_password = self.generate_random_password()

                # Create user based on role
                if role.lower() == "super":
                    user = User.objects.create_superuser(username=username, email=email, password=random_password)
                else:
                    user = User.objects.create_user(username=username, email=email, password=random_password)

                if phone_number:
                    user.phone_numbers = phone_number
                    user.save()

                # Send email with generated password
                send_mail(
                    subject="Your New Account Credentials",
                    message=f"Hello {username},\n\nYour account has been created successfully.\n\n"
                            f"Username: {username}\n"
                            f"Password: {random_password}\n\n"
                            f"Please change your password after logging in.",
                    from_email=settings.DEFAULT_FROM_EMAIL,  # Replace with your actual email
                    recipient_list=[email],
                    fail_silently=False,
                )

            return Response({"message": "User created successfully. Password sent to email.", "status": status.HTTP_201_CREATED},status=status.HTTP_201_CREATED)
        
        except Exception as e:
            print(str(e))
            return Response({"message": "Failed to create user","error": str(e),"status": status.HTTP_500_INTERNAL_SERVER_ERROR}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DashboardOverview(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_active_subscriptions = Subscription.objects.filter(status="Active").count()
        total_hardware_items = Hardware.objects.count()
        total_active_customers = Customer.objects.filter(status="Active").count()

        return Response({
            "total_active_subscriptions": total_active_subscriptions,
            "total_hardware_items": total_hardware_items,
            "total_active_customers": total_active_customers
        })

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """View user profile."""
        user = request.user
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response({"status":status.HTTP_200_OK},serializer.data)

    def put(self, request):
        """Update user profile."""
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"user updated successfully","status":status.HTTP_200_OK},serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubscriptionCountView(APIView):
    """Fetch the count of active and expired subscriptions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_count = Subscription.objects.filter(next_payement_date__gte=now()).count()
        expired_count = Subscription.objects.filter(next_payement_date__lt=now()).count()

        return Response({
            "total_active_subscriptions": active_count,
            "total_expired_subscriptions": expired_count,
            'status': status.HTTP_200_OK,
        })

class ActiveSubscriptionsView(generics.ListAPIView):
    """Fetch all active subscriptions (not expired)."""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(end_date__gte=now())

class ExpiredSubscriptionsView(generics.ListAPIView):
    """Fetch all expired subscriptions."""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Subscription.objects.filter(end_date__lt=now())

class WarningSubscriptionsView(generics.ListAPIView):
    """Fetch subscriptions with upcoming due payments (within the next 7 days)."""
    
    serializer_class = SubscriptionWarningSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        today = now().date()
        next_week = today + timedelta(days=7)
        # return Subscription.objects.filter(next_payment_date__range=[today, next_week])
        return (
            Subscription.objects.filter(next_payment_date__range=[today, next_week],is_deleted=False)
            .select_related(
                "provider", "billing", "software_detail", "domain", "server"
            )  # Optimized DB queries
        )

class SubscriptionCategoryDistributionView(APIView):
    """Returns the percentage distribution of subscription categories."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        total_subscriptions = Subscription.objects.filter(is_deleted=False).count()

        if total_subscriptions == 0:
            return Response({"message": "No active subscriptions found", "data": {}})

        category_counts = Subscription.objects.filter(is_deleted=False).values('subscription_category').annotate(count=Count('id'))

        category_distribution = {
            category['subscription_category']: round((category['count'] / total_subscriptions) * 100, 2)
            for category in category_counts
        }

        return Response({"total_subscriptions": total_subscriptions, "category_distribution": category_distribution})

class SubscriptionMonthlyAnalysisView(APIView):
    """Returns month-wise subscription counts for each category."""
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        subscriptions = (
            Subscription.objects.filter(is_deleted=False)
            .annotate(month=TruncMonth('start_date'))
            .values('month', 'subscription_category')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Structure the data for line chart
        monthly_data = {}
        for entry in subscriptions:
            month_str = entry['month'].strftime('%Y-%m')  # Format as YYYY-MM
            category = entry['subscription_category']
            count = entry['count']

            if month_str not in monthly_data:
                monthly_data[month_str] = {
                    'software': 0,
                    'billing': 0,
                    'server': 0,
                    'domain': 0
                }
            monthly_data[month_str][category] = count

        return Response({'monthly_analysis': monthly_data})

class ProviderCreateView(generics.CreateAPIView):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # provider_name = request.data.get("provider_name")

        # # Check if provider already exists
        # if Provider.objects.filter(provider_name=provider_name).exists():
        #     return Response({"error": "Provider already exists!"}, status=status.HTTP_400_BAD_REQUEST)
        
        print("Request Data:", request.data)
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            try:
                serializer.save()
                return Response(
                    { "status": status.HTTP_201_CREATED,
                    "message": "Provider created successfully",
                    "data": serializer.data},
                    status=status.HTTP_201_CREATED
                )
            except IntegrityError as e:  # Catch IntegrityError
                print("Database Error:", str(e))
                return Response(
                    {"message": "Provider already exists", "status": status.HTTP_400_BAD_REQUEST},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        print("Serializer Errors:", serializer.errors)  # Print detailed errors
        return Response(
            {"message": "Validation failed", "status": status.HTTP_400_BAD_REQUEST, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

class ProviderListView(generics.ListAPIView):
    queryset = Provider.objects.all()
    # queryset = Provider.objects.all().only("id", "provider_name")
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]  # Ensure anyone can access it

    def get_queryset(self):
        queryset = Provider.objects.all()
        # queryset = Provider.objects.only("id", "provider_name")
        print("\n*************************************************************************************************************************************")
        print("Providers List:", list(queryset.values("id", "provider_name")))  # Print all providers
        print("\n************************************************************************************************************************************")
        return queryset

class SubscriptionChoicesView(APIView):
    permission_classes = [AllowAny]  # Allow public access

    def get(self, request, *args, **kwargs):
        choices = {
            "category_choices": Subscription.CATEGORY_CHOICES,
            # "payment_status_choices": Subscription.PAYMENT_STATUS_CHOICES,
            # "status_choices": Subscription.STATUS_CHOICES,
        }
        return Response(choices)

class SubscriptionCreateView(generics.CreateAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print("\n***********************************************************************************************************************************")
        print("Request Data:", request.data)
        print("\n***********************************************************************************************************************************")

        data = request.data.copy()

        # Convert frontend camelCase to backend snake_case
        field_mapping = {
            "subscriptionCategory": "subscription_category",
            "status": "status",
            "startDate": "start_date",
            "endDate": "end_date",
            "paymentMethod": "payment_method",
            "notificationMethod": "notification_method",
            "customMessage": "custom_message",
            "billingCycle": "billing_cycle",
            "daysBeforeEnd": "optional_days_before",
            "firstReminderMonth": "reminder_months_before",
            "reminderDay": "reminder_days_before",
        }

        for frontend_key, backend_key in field_mapping.items():
            if frontend_key in data:
                value = data.pop(frontend_key)
                if backend_key in ["optional_days_before", "reminder_months_before", "reminder_days_before"] and value == "":
                    data[backend_key] = None
                else:
                    data[backend_key] = value

        print("Modified Data:", data)
        print("\n***********************************************************************************************************************************")

        required_fields = ["providerid", "subscription_category", "start_date", "billing_cycle", "cost", "payment_method"]
        for field in required_fields:
            if not data.get(field):
                return Response({"message": f"{field.replace('_', ' ').title()} is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Check for existing subscription
        # existing_subscription = Subscription.objects.filter(user=request.user,provider_id=data.get("provider"),subscription_category=data.get("subscription_category"),is_deleted=False).exists()
        existing_subscription =  Subscription.objects.filter(
            user=request.user,
            provider_id=data.get("provider"),
            subscription_category=data.get("subscription_category"),
            billing_cycle=data.get("billing_cycle"),
            cost=data.get("cost"),
            payment_method=data.get("payment_method"),
            start_date=data.get("start_date"),
            is_deleted=False
        ).exists() or SoftwareSubscriptions.objects.filter(software_id=data.get("software_id")).exists() or Utilities.objects.filter(consumer_no=data.get("consumer_no")).exists() or Domain.objects.filter(domain_name=data.get("domain_name")).exists() or Servers.objects.filter(server_name=data.get("server_name")).exists()
            # return Response({"error": "Duplicate subscription or related record exists."}, status=400)

        if existing_subscription:
            return Response(
                {"message": "A similar active subscription already exists.","status":status.HTTP_400_BAD_REQUEST},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set default values
        data["status"] = "Active"
        data["payment_status"] = "Paid"
        data["user"] = request.user.id
        print("Final Data Before Saving:", data)

        provider_id = data.get("providerid")
        print(" Selected Provider ID:", provider_id)

        if not provider_id:
            return Response({"message": "Provider ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            provider = Provider.objects.get(id=provider_id)
        except Provider.DoesNotExist:
            return Response({"message": "Invalid Provider ID."}, status=status.HTTP_400_BAD_REQUEST)

        data["provider"] = provider.id
        additional_fields = data.pop("additionalDetails", {})
        reminder_fields = [
            "reminder_days_before", "reminder_months_before", "reminder_day_of_month",
            "notification_method", "recipients", "custom_message", "optional_days_before"
        ]
        reminder_data = {key: data.pop(key) for key in reminder_fields if key in data}
        print(reminder_data)

        # Validate and create subscription
        serializer = self.get_serializer(data=data)
        if not serializer.is_valid():
            print("Serializer Errors:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                subscription = serializer.save()
                print("Subscription created:", subscription)

                # Handle category-specific data
                category = subscription.subscription_category
                if category == "Software":
                    # Check for existing software subscription
                    # if SoftwareSubscriptions.objects.filter(subscription=subscription).exists():
                    # if SoftwareSubscriptions.objects.filter(software_id=additional_fields.get("software_id")).exists():
                    #     raise ValidationError("A software subscription with this ID already exists.")
                    SoftwareSubscriptions.objects.create(subscription=subscription, **additional_fields)
                elif category == "Billing":
                    utility_instance = Utilities(subscription=subscription, **additional_fields)
                    # utility_instance.clean()
                    utility_instance.save()
                elif category == "Domain":
                    Domain.objects.create(subscription=subscription, **additional_fields)
                elif category == "Server":
                    Servers.objects.create(subscription=subscription, **additional_fields)

                # Apply default reminder settings if none provided
                if not any(reminder_data.values()):
                    if subscription.billing_cycle in ["weekly", "monthly"]:
                        reminder_data["reminder_days_before"] = 3
                    else:
                        reminder_data["reminder_months_before"] = 1
                        reminder_data["reminder_day_of_month"] = 1

                    reminder_data.update({
                        "notification_method": "email",
                        "reminder_type": "renewal",
                        "recipients": request.user.email,
                        "custom_message": "Your subscription is due soon. Please renew it in time."
                    })

                # Create Reminder if data exists
                if any(reminder_data.values()):
                    reminder = Reminder.objects.create(
                        reminder_days_before=reminder_data.get("reminder_days_before"),
                        reminder_months_before=reminder_data.get("reminder_months_before"),
                        reminder_day_of_month=reminder_data.get("reminder_day_of_month"),
                        optional_days_before=reminder_data.get("optional_days_before"),
                        notification_method=reminder_data.get("notification_method"),
                        recipients=reminder_data.get("recipients"),
                        custom_message=reminder_data.get("custom_message"),
                        reminder_type="renewal",
                    )

                    ReminderSubscription.objects.create(reminder=reminder, subscription=subscription)

                    reminder_dates = reminder.calculate_all_reminder_dates(subscription)
                    print("Reminder Dates:", reminder_dates)

                    if reminder_dates:
                        reminder.reminder_date = reminder_dates[0]
                        reminder.save()
                        print("Reminder Date Saved:", reminder.reminder_date)

                return Response({
                    'message':"Subscription Added Succussfully",
                    'status': status.HTTP_201_CREATED,
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            print(f"Validation Error: {str(e)}")
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error creating subscription: {str(e)}")
            return Response({"message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubscriptionListView(generics.ListAPIView):
    """
    API endpoint to view detailed subscription data including related fields.
    """
    # queryset = Subscription.objects.prefetch_related(
    #     "software_detail", "billing", "domain", "server"
    # ).all()
    queryset = Subscription.objects.filter(is_deleted=False).select_related("provider").prefetch_related(
        "software_detail", "billing", "domain", "server"
    ).all()
    
    serializer_class = SubscriptionDetailSerializer
    permission_classes = [permissions.IsAuthenticated]
    # filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    # filterset_fields = ["subscription_category", "provider", "payment_status"]
    # ordering_fields = ["start_date", "end_date", "next_payment_date", "provider"]
    # search_fields = [
    #     "software_detail__software_name",
    #     "server__server_name",
    #     "domain__domain_name",
    #     "billing__utility_type",
    # ]

class SubscriptionDetailView(generics.RetrieveAPIView):
    queryset = Subscription.objects.all()
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.AllowAny]  # Only admin users can access
    lookup_field = "id"

    def get(self, request, *args, **kwargs):
        subscription = get_object_or_404(Subscription, id=kwargs["id"])
        serializer = self.get_serializer(subscription)

        # Highlight expired subscriptions
        data = serializer.data
        if subscription.end_date and subscription.end_date < timezone.now().date():
            data["status"] = "Expired"
            data["highlight"] = "red"

        return Response(data, status=status.HTTP_200_OK)

class SubscriptionDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Subscription.objects.filter(is_deleted=False).select_related(
        "provider"
    ).prefetch_related(
        "software_detail", "billing", "domain", "server"
    )
    # print(queryset)
    
    # Use different serializers for different actions
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return SubscriptionUpdateSerializer
        return SubscriptionDetailSerializer
    
    permission_classes = [permissions.IsAuthenticated]

    def perform_update(self, serializer):
        instance=serializer.save(updated_by=self.request.user)
        # Set history tracking info
        # update_change_reason(instance, f"Updated subscription by {self.request.user}")
        instance.history_user = self.request.user
        instance.save()  # Must call save() to persist history_user
        logger.info(f"Subscription {instance.id} updated successfully by {self.request.user}")

    def perform_destroy(self, instance):
        print(f"Soft deleting subscription with ID: {instance.id}")
        # Track soft delete reason
        # update_change_reason(instance, f"Soft deleted by {self.request.user}")
        instance.history_user = self.request.user
        instance.save()
        instance.soft_delete(deleted_by=self.request.user)

    def patch(self, request, *args, **kwargs):
        if 'providerName' in request.data:
            try:
                provider = Provider.objects.get(provider_name=request.data['providerName'])
                request.data['provider_id'] = provider.id
            except Provider.DoesNotExist:
                return Response(
                    {"error": "Provider not found"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        logger.debug(f"Received PATCH request with data: {request.data}")
        try:
            response = self.partial_update(request, *args, **kwargs)
            logger.info(f"Subscription {kwargs.get('pk')} patched successfully.")
            return Response({"status": status.HTTP_200_OK, "message": "Subscription updated successfully.","data": response.data}, status=status.HTTP_200_OK)
        except ValidationError as e:
            logger.error(f"Validation error while updating subscription: {str(e)}")
            return Response({"error": str(e)},status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Unexpected error while updating subscription.")
            return Response({"error": str(e)},status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExpenditureAnalysisView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        current_year = datetime.now().year
        logger.info("Fetching expenditure data for analysis...")

        # Aggregate expenses by year & month
        software_expenses = (
            SoftwareSubscriptions.objects
            .annotate(year=ExtractYear('subscription__start_date'), month=ExtractMonth('subscription__start_date'))
            .values('year', 'month')
            .annotate(total=Sum('subscription__cost'))
        )
        logger.info(f"Software expenses: {list(software_expenses)}")

        server_expenses = (
            Servers.objects
            .annotate(year=ExtractYear('subscription__start_date'), month=ExtractMonth('subscription__start_date'))
            .values('year', 'month')
            .annotate(total=Sum('subscription__cost'))
        )
        logger.info(f"Server expenses: {list(server_expenses)}")

        domain_expenses = (
            Domain.objects
            .annotate(year=ExtractYear('subscription__start_date'), month=ExtractMonth('subscription__start_date'))
            .values('year', 'month')
            .annotate(total=Sum('subscription__cost'))
        )
        logger.info(f"Domain expenses: {list(domain_expenses)}")

        utility_expenses = (
            Utilities.objects
            .annotate(year=ExtractYear('subscription__start_date'), month=ExtractMonth('subscription__start_date'))
            .values('year', 'month')
            .annotate(total=Sum('subscription__cost'))
        )
        logger.info(f"Utility expenses: {list(utility_expenses)}")

        # Store data in a structured format
        expenditure_data = defaultdict(lambda: {'Software': 0, 'Server': 0, 'Domain': 0, 'Utility': 0})

        # Populate data from each expense type
        for entry in software_expenses:
            expenditure_data[(entry['year'], entry['month'])]['Software'] = entry['total']

        for entry in server_expenses:
            expenditure_data[(entry['year'], entry['month'])]['Server'] = entry['total']

        for entry in domain_expenses:
            expenditure_data[(entry['year'], entry['month'])]['Domain'] = entry['total']

        for entry in utility_expenses:
            expenditure_data[(entry['year'], entry['month'])]['Utility'] = entry['total']

        logger.info(f"Aggregated expenditure data: {dict(expenditure_data)}")

        # Convert structured data into the required format
        formatted_data = [
            {
                "month": datetime(year, month, 1).strftime('%b'),
                "Software": data["Software"],
                "Server": data["Server"],
                "Domain": data["Domain"],
                "Utility": data["Utility"],
                "year": year
            }
            for (year, month), data in sorted(expenditure_data.items())
        ]
        logger.info(f"Final formatted expenditure data: {formatted_data}")

        return Response(formatted_data)

class SubscriptionReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        logger.info("Fetching subscription data for report...")
        
        # Fetch current year
        current_year = datetime.now().year

        # Define categories
        categories = {
            "software": SoftwareSubscriptions,
            "server": Servers,
            "domain": Domain,
            "utility": Utilities
        }

        # Store data in a structured format
        expenditure_data = defaultdict(lambda: {"software": 0, "server": 0, "domain": 0, "utility": 0})

        # Populate data from each category
        for category, model in categories.items():
            expenses = (
                model.objects
                .annotate(year=ExtractYear('subscription__start_date'), month=ExtractMonth('subscription__start_date'))
                .values('year', 'month')
                .annotate(total=Sum('subscription__cost'))
            )
            
            for entry in expenses:
                expenditure_data[(entry['year'], entry['month'])][category] = entry['total']

        logger.info(f"Aggregated subscription data: {dict(expenditure_data)}")

        # Format data as per required output
        formatted_data = defaultdict(list)
        for (year, month), data in sorted(expenditure_data.items()):
            formatted_data[str(year)].append({
                "month": datetime(year, month, 1).strftime('%B'),
                "software": data["software"],
                "domain": data["domain"],
                "server": data["server"],
                "utility": data["utility"],
                "total": data["software"] + data["domain"] + data["server"] + data["utility"]
            })

        logger.info(f"Final formatted subscription report: {formatted_data}")
        return Response(formatted_data)

class HardwareSummaryView(APIView):
    def get(self, request):
        total_hardware = Hardware.objects.filter(is_deleted=False).count()
        warranty_expiring = Hardware.objects.filter(
            is_deleted=False,
            warranty__warranty_expiry_date__lte=now() + timedelta(days=30)
        ).count()
        maintenance_due = Hardware.objects.filter(status='maintenance_due', is_deleted=False).count()
        out_of_warranty = Hardware.objects.filter(
            is_deleted=False,
            warranty__warranty_expiry_date__lte=now()
        ).count()

        return Response({
            "total_hardware": total_hardware,
            "warranty_expiring": warranty_expiring,
            "maintenance_due": maintenance_due,
            "out_of_warranty": out_of_warranty
        })

class UpcomingHardwareAPIView(APIView):
    def get(self, request):
        upcoming_date = now().date() + timedelta(days=30)  # Next 30 days

        # Fetch hardware with upcoming warranty expiration
        expiring_warranty_hardware = Hardware.objects.filter(
            is_deleted=False,
            warranty__warranty_expiry_date__lte=upcoming_date
        ).distinct()

        # Fetch hardware with upcoming service dates (Fixed Calculation)
        upcoming_service_hardware = Hardware.objects.filter(
            is_deleted=False,
            service__last_service_date__isnull=False
        ).annotate(
            next_service_due_date=ExpressionWrapper(
                F("service__last_service_date") + F("service__service_period") * timedelta(days=1),
                output_field=DateField()
            )
        ).filter(next_service_due_date__lte=upcoming_date).distinct()

        # Combine results (avoid duplicates)
        hardware_with_upcoming_events = expiring_warranty_hardware | upcoming_service_hardware

        # Serialize response
        data = [
            {
                "hardware_name": hw.hardware_name,
                "serial_number": hw.serial_number,
                "warranty_expiry_date": getattr(hw.warranty, 'warranty_expiry_date', None),
                "next_service_date": getattr(hw.service, 'next_service_date', None)
            }
            for hw in hardware_with_upcoming_events
        ]

        return Response({"upcoming_hardware": data})

class AddHardwareAPIView(APIView):
    permission_classes=[IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        print("\n*************************************************************************************************************************************")
        logger.info("Received request data: %s", request.data)
        # serializer = HardwareSerializer(data=request.data)
        # serializer = HardwareSerializer(data=request.data, context={'request': request})
        # Convert frontend fields to match backend model
        converted_data = self.convert_frontend_to_backend(request.data)
        print("\n*************************************************************************************************************************************")
        # logger.info("Converted data: %s", converted_data)

        converted_data["user"] = request.user.id
        converted_data["status"] = "Active"
        logger.info("Converted data: %s", converted_data)

        if Hardware.objects.filter(serial_number=converted_data["serial_number"]).exists():
            return Response({"message": "Duplicate serial number","status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = HardwareSerializer(data=converted_data, context={'request': request}) 
 
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    hardware=serializer.save(user=request.user)
                    logger.info("Successfully added hardware: %s", hardware)

                    # Extract reminder-related fields from the request data.
                    reminder_field_mapping = {
                        "reminderType": "reminder_type",
                        "reminderDaysBefore": "reminder_days_before",
                        "reminderMonthsBefore": "reminder_months_before",
                        "reminderDayOfMonth": "reminder_day_of_month",
                        "notificationMethod": "notification_method",
                        "recipients": "recipients",
                        "customMessage": "custom_message",
                        "optionalDaysBefore": "optional_days_before",
                    }

                    maintenance_reminder_data = {}
                    for frontend_key, backend_key in reminder_field_mapping.items():
                        if frontend_key in request.data:
                            maintenance_reminder_data[backend_key] = request.data[frontend_key]

                    # ✅ Apply default reminder settings if none provided (optional)
                    if not any(maintenance_reminder_data.values()):
                        maintenance_reminder_data.update({
                            "reminder_type": "maintenance",
                            "reminder_days_before": 3,
                            "notification_method": "email",
                            "recipients": request.user.email,
                            "custom_message": f"Your hardware {hardware.hardware_type} (SN: {hardware.serial_number}) maintenance is scheduled soon. Please check your service details.",
                            "reminder_status": "pending"
                        })
                    # Create warranty reminder
                    warranty_reminder_data = {
                        "reminder_type": "warranty",
                        "reminder_days_before": 3,  # 30 days before warranty expires
                        "notification_method": "email",
                        "recipients": request.user.email,
                        "custom_message": f"Warranty for your {hardware.hardware_type} (SN: {hardware.serial_number}) is expiring soon.",
                        "reminder_status": "pending"
                    }

                    # Create both reminders
                    for reminder_data, reminder_name ,reminder_type in [
                        (maintenance_reminder_data, "Maintenance","maintenance"),
                        (warranty_reminder_data, "Warranty","warranty")
                    ]:
                        try:
                            reminder = Reminder.objects.create(
                                reminder_type=reminder_data.get("reminder_type"),
                                reminder_days_before=reminder_data.get("reminder_days_before"),
                                reminder_months_before=reminder_data.get("reminder_months_before"),
                                reminder_day_of_month=reminder_data.get("reminder_day_of_month"),
                                optional_days_before=reminder_data.get("optional_days_before"),
                                notification_method=reminder_data.get("notification_method"),
                                recipients=reminder_data.get("recipients"),
                                custom_message=reminder_data.get("custom_message"),
                                reminder_status=reminder_data.get("reminder_status", "pending"),
                            )
                            ReminderHardware.objects.create(reminder=reminder, hardware=hardware,reminder_type=reminder_type)
                            logger.info(f"{reminder_name} reminder created and linked to hardware: {reminder}")
                        
                        except Exception as e:
                            logger.error(f"Failed to create {reminder_name.lower()} reminder: {str(e)}")
                            continue
            
                    return Response({
                        "message": "Hardware successfully added.",
                        "data": serializer.data,
                        "status": status.HTTP_201_CREATED
                    }, status=status.HTTP_201_CREATED)
            
            except Exception as e:
                logger.error("Error while saving hardware or reminders: %s", str(e))
                return Response({"message": "Failed to add hardware due to a server error."},
                                status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if not serializer.is_valid():
            logger.info("HardwareSerializer validation errors: %s", serializer.errors)
            # error_messages = " ".join([f"{key}: {', '.join(value)}" for key, value in serializer.errors.items()])
            # return Response({"message": f"Failed to add hardware. {error_messages}"}, status=status.HTTP_400_BAD_REQUEST)
    
            return Response({
            "message": "Failed to add hardware. Please check the input data.",
            "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        
    def convert_frontend_to_backend(self, data):
        try:

            extended_warranty_period = data.get("extendedWarrantyPeriod", "").strip()
            if extended_warranty_period == "":
                extended_warranty_period = None
            else:
                try:
                    extended_warranty_period = int(extended_warranty_period)
                except ValueError:
                    extended_warranty_period = None
            converted = {
                "hardware_type": data.get("deviceType"),
                "manufacturer": data.get("manufacturer"),
                "model_number": data.get("model"),
                "serial_number": data.get("serialNumber"),
                "assigned_department": data.get("assignedTo"),
                "notes": data.get("notes"),
                "vendor_contact":data.get("vendor_contact"),
                "vendor_email":data.get("vendor_email"),
                "vendor_name":data.get("vendor_name"),
                
                # "status": "active",  # Set default status
                "purchase": {
                    "purchase_date": parse_date(data.get("purchaseDate")),
                    "purchase_cost": data.get("purchasecost")
                },
                "warranty": {
                    "warranty_expiry_date": parse_date(data.get("warrantyExpiryDate")),
                    "is_extended_warranty": data.get("isExtendedWarranty", False),
                    "extended_warranty_period": extended_warranty_period,
                },
                "services": {
                    "last_service_date": parse_date(data.get("lastServiceDate")),
                    "next_service_date": parse_date(data.get("nextServiceDate")),
                    "free_service_until": parse_date(data.get("freeServiceUntil")),
                    "service_cost": Decimal(data["serviceCost"]) if data.get("serviceCost") else None,
                    "service_provider": data.get("serviceProvider"),
                },
                
            }
            
            if data.get("deviceType") == "Mobile Phone":
                converted["portable_device"] = {
                    "device_type": "Mobile Phone",
                    "os_version": data.get("OS_Version"),
                    "storage": data.get("Storage"),
                    "imei_number": data.get("IMEI_Number"),
                }
            if data.get("deviceType") == "Tablet":
                converted["portable_device"] = {
                    "device_type": "Tablet",
                    "os_version": data.get("OS_Version"),
                    "storage": data.get("Storage"),
                    "imei_number": data.get("IMEI_Number"),
                }

            if data.get("deviceType") == "Laptop":
                converted["computer"] = {
                    "computer_type": "Laptop",
                    "cpu": data.get("CPU"),
                    "ram": data.get("RAM"),
                    "storage": data.get("Storage"),
                }
            if data.get("deviceType") == "Desktop":
                converted["computer"] = {
                    "computer_type": "Desktop",
                    "cpu": data.get("CPU"),
                    "ram": data.get("RAM"),
                    "storage": data.get("Storage"),
                }
            if data.get("deviceType") == "On-Premise Server":
                converted["computer"] = {
                    "computer_type": "Server",
                    "cpu": data.get("CPU"),
                    "ram": data.get("RAM"),
                    "storage": data.get("Storage"),

                    "operating_system": data.get("Operating_System"),
                    "hardware_server_name": data.get("Server_Name"),
                }

            if data.get("deviceType") == "Network Device":
                converted["network_device"] = {
                    "throughput": data.get("Throughput"),
                    "ip_address": data.get("IP_Address"),
                    "name_specification": data.get("Name_Specification"),
                }
            if data.get("deviceType") == "Air Conditioner":
                converted["air_conditioner"] = {
                    "btu_rating": data.get("BTU_Rating"),
                    "energy_rating": data.get("EnergyP_Rating"),
                }
            # if data.get("deviceType") == "On-Premise Server":
            #     converted["on_premise_server"] = {
            #         "cpu": data.get("CPU"),
            #         "ram": data.get("RAM"),
            #         "storage_configuration": data.get("Storage_Configuration"),
            #         "operating_system": data.get("Operating_System"),
            #     }
            if data.get("deviceType") == "Printer":
                converted["printer"] = {
                    "print_technology": data.get("Print_Technology"),
                    "print_speed": data.get("Print_Speed"),
                    "connectivity": data.get("Connectivity"),
                }
            if data.get("deviceType") == "Scanner":
                converted["scanner"] = {
                    "scan_resolution": data.get("Scan_Resolution"),
                    "scan_type": data.get("Scan_Type"),
                    "connectivity": data.get("Connectivity"),
                }
            
            return converted
        
        except Exception as e:
                logger.exception("Error while converting frontend data to backend model format: %s", str(e))
                return {}

class ListHardwareView(generics.ListAPIView):
    # queryset = Hardware.objects.all()
    queryset = Hardware.objects.filter(is_deleted=False)
    serializer_class = HardwareSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Allow filtering by Type, Manufacturer, Purchase Date, Assigned Department, Status
    filterset_fields = ['hardware_type', 'manufacturer', 'purchase__purchase_date', 'assigned_department', 'status']
    
    # Allow searching by manufacturer name or assigned department
    search_fields = ['manufacturer', 'assigned_department']

    # Allow sorting by purchase date or status
    ordering_fields = ['purchase__purchase_date', 'status']

    def get_queryset(self):
        # queryset = Hardware.objects.all()
        queryset = Hardware.objects.filter(is_deleted=False)
        ordering = self.request.query_params.get('ordering', 'purchase__purchase_date')

        if ordering == "purchase__purchase_date":
            return queryset.order_by(F('purchase__purchase_date').asc(nulls_last=True))
        elif ordering == "-purchase__purchase_date":
            return queryset.order_by(F('purchase__purchase_date').desc(nulls_last=True))
        else:
            return queryset.order_by(ordering)

class RetrieveUpdateDestroyHardwareView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Hardware.objects.filter(is_deleted=False)
    # queryset = Hardware.objects.all().prefetch_related(
    #     'purchase', 'warranty', 'services',
    #     'computer', 'portable_device', 'network_device',
    #     'air_conditioner', 'printer', 'scanner'
    # )
    serializer_class = HardwareSerializer
    permission_classes = [IsAuthenticated]

    # Optionally override update() if you need custom behavior
    def update(self, request, *args, **kwargs):
        # Log incoming data if needed
        print("Update Request Data:", request.data)
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            hardware = serializer.save()
            return Response({
                "message": "Hardware successfully updated.",
                "data": HardwareSerializer(hardware, context={'request': request}).data,
                "status": status.HTTP_200_OK
            }, status=status.HTTP_200_OK)
        
        print("Update Serializer Errors:", serializer.errors)
        return Response({
            "message": "Failed to update hardware. Please check the input data.",
            "errors": serializer.errors,
        }, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to implement soft delete"""
        try:
            instance = self.get_object()
            instance.soft_delete(deleted_by=request.user)  # Call soft delete method
            return Response(
                {"message": "Hardware successfully deleted.","status":status.HTTP_200_OK}, 
                status=status.HTTP_200_OK
            )
        except Hardware.DoesNotExist:
            return Response({"message": "hardware not found or already deleted."}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def spending_report(request):
    """Generate spending report for hardware-related purchases, services, and warranties."""
    
    # Get filters from request
    category = request.GET.get('category')  # e.g., "Laptop", "Server"
    department = request.GET.get('department')  # e.g., "IT", "HR"
    start_date = request.GET.get('start_date')  # e.g., "2024-01-01"
    end_date = request.GET.get('end_date')  # e.g., "2024-12-31"

    # Filter hardware based on category and department
    hardware_queryset = Hardware.objects.all()
    if category:
        hardware_queryset = hardware_queryset.filter(hardware_type=category)
    if department:
        hardware_queryset = hardware_queryset.filter(assigned_department=department)

    # Get hardware IDs for further filtering
    hardware_ids = hardware_queryset.values_list('id', flat=True)

    # Filter purchases
    purchases = Purchase.objects.filter(hardware_id__in=hardware_ids)
    if start_date and end_date:
        purchases = purchases.filter(purchase_date__range=[start_date, end_date])
    total_purchase_cost = purchases.aggregate(total=Sum('purchase_cost'))['total'] or 0

    # Filter services
    services = HardwareService.objects.filter(hardware_id__in=hardware_ids)
    if start_date and end_date:
        services = services.filter(last_service_date__range=[start_date, end_date])
    total_service_cost = services.aggregate(total=Sum('service_cost'))['total'] or 0

    # Filter warranties
    warranties = Warranty.objects.filter(hardware_id__in=hardware_ids)
    if start_date and end_date:
        warranties = warranties.filter(warranty_expiry_date__range=[start_date, end_date])
    extended_warranty_cost = warranties.filter(is_extended_warranty=True).count() * 500  # Assume ₹500 per extension

    # Total Spending Calculation
    total_spending = total_purchase_cost + total_service_cost + extended_warranty_cost

    return Response({
        "total_spending": total_spending,
        "purchase_cost": total_purchase_cost,
        "service_cost": total_service_cost,
        "extended_warranty_cost": extended_warranty_cost,
        "total_items": hardware_queryset.count(),
    })

@api_view(['GET'])
def hardware_report(request):
    """Fetch hardware report with filters"""
    category = request.GET.get('category')
    warranty_status = request.GET.get('warranty_status')

    queryset = Hardware.objects.all()
    if category:
        queryset = queryset.filter(hardware_type=category)
    if warranty_status:
        queryset = queryset.filter(warranty_status=warranty_status)

    data = [
        {
            "hardware_name": hw.hardware_name,
            "type": hw.hardware_type,
            # "purchase_date": hw.purchase_date.strftime("%Y-%m-%d"),
            "purchase_date": hw.purchase.purchase_date.strftime("%Y-%m-%d") if hasattr(hw, 'purchase') else None,
            # "warranty_status": hw.warranty_status,
            "warranty_status": hw.warranty.warranty_expiry_date.strftime("%Y-%m-%d") if hasattr(hw, 'warranty') else None,
            # "maintenance_status": hw.maintenance_status,
            "maintenance_status": "Under Maintenance" if hw.status == 'maintenance' else "Not in Maintenance",
            "department": hw.assigned_department,
        }
        for hw in queryset
    ]
    return Response({"hardware_report": data})

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklist the token

            return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ReminderAPIView(APIView):
    """
    API view for handling reminders.
    Supports GET (list), POST (create), PUT (update).
    """

    def get(self, request, pk=None):
        """Retrieve a single reminder or list all reminders."""
        if pk:
            reminder = get_object_or_404(Reminder, pk=pk)
            serializer = ReminderSerializer(reminder)
            return Response(serializer.data, status=status.HTTP_200_OK)
        reminders = Reminder.objects.all()
        serializer = ReminderSerializer(reminders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new reminder."""
        serializer = ReminderSerializer(data=request.data)
        if serializer.is_valid():
            reminder = serializer.save()
            return Response(
                {"message": "Reminder created successfully!", "reminder": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        """Update an existing reminder."""
        reminder = get_object_or_404(Reminder, pk=pk)
        serializer = ReminderSerializer(reminder, data=request.data, partial=True)
        if serializer.is_valid():
            reminder = serializer.save()
            return Response(
                {"message": "Reminder updated successfully!", "reminder": serializer.data},
                status=status.HTTP_200_OK
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResourceNameListView(generics.ListAPIView):
    serializer_class = ResourceNameSerializer
    permission_classes = [IsAuthenticated]  # Optional: restrict access to authenticated users

    def get_queryset(self):
        resource_type = self.request.query_params.get('type')
        print("resource_type:",resource_type)
        if resource_type:
            return Resource.objects.filter(resource_type=resource_type, is_deleted=False)
        return Resource.objects.none()  # Return empty if no resource_type is provided

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"message": "No resources found for the given type."}, status=404)
        return super().list(request, *args, **kwargs)

class ResourceCreateView(generics.CreateAPIView):
    serializer_class = ResourceAddSerializer
    permission_classes = [IsAuthenticated]  # Restrict access to authenticated users

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            if serializer.is_valid():
                serializer.save(user=request.user)
                return Response(
                    {"message": "Resource added successfully!", "resource": serializer.data,"status":status.HTTP_201_CREATED},
                    status=status.HTTP_201_CREATED
                )
        except ValidationError as e:
            # return Response({"message": e.detail,"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)
            error_messages = e.detail  # Extract error details
            print("error message:",error_messages)
            error_text = " ".join([f"{key}: {', '.join(val)}" for key, val in error_messages.items()])  # Convert dict to text
            print("error text:",error_text)

            return Response(
                {"message": error_text, "status": status.HTTP_400_BAD_REQUEST}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print("Serializer Errors:", serializer.errors)
        return Response({"message":serializer.errors,"status":status.HTTP_400_BAD_REQUEST}, status=status.HTTP_400_BAD_REQUEST)

class DashboardOverviewAll(APIView):
    permission_classes = [IsAuthenticated]  # Secure the endpoint

    def get(self, request):
        today = now().date()
        next_week = today + timedelta(days=7)
        next_month = today.replace(day=1) + timedelta(days=32)  # Approx next month start
        first_day_of_year = today.replace(month=1, day=1)
        last_day_of_year = today.replace(month=12, day=31)

        # Active Counts
        # total_active_subscriptions = Subscription.objects.filter(status="Active").count()
        total_active_customers = Customer.objects.filter(status="Active",is_deleted=False).count()
        total_active_hardware = Hardware.objects.filter(status="Active",is_deleted=False).count()
        total_hardware=Hardware.objects.filter(is_deleted=False).count()

        # active_count = Subscription.objects.filter(end_date__gte=now()).count()
        active_count = Subscription.objects.filter(status="Active",is_deleted=False).count()
        # active_count = Subscription.objects.all.count()
        print(f"active count {active_count}")
        # expired_count = Subscription.objects.filter(end_date__lt=now()).count()
        expired_count = Subscription.objects.filter(status="Expired").count()
        print(f"expired count {expired_count}")

        # Monthly Cost Analysis
        # Get first and last day of the current month
        today = now().date()
        first_day = today.replace(day=1)
        #  Total subscription cost for the current month
        total_subscription_cost = Subscription.objects.filter(
            status="Active",
            start_date__gte=first_day,  # Ensure the subscription started in the current month
        ).aggregate(total_cost=Sum("cost"))["total_cost"] or 0
        # total_subscription_cost = Subscription.objects.filter(status="Active").aggregate(total_cost=Sum("cost"))["total_cost"] or 0

        #  Total hardware cost (purchase + maintenance) for the current month
        # purchase_cost = Hardware.objects.filter(
        #     is_deleted=False,
        #     purchase__purchase_date__gte=first_day  # Ensure the purchase was in the current month
        # ).aggregate(total_cost=Sum("purchase__purchase_cost"))["total_cost"] or 0
        purchase_cost = Hardware.objects.filter(
            is_deleted=False,
            purchase__purchase_date__gte=first_day_of_year,
            purchase__purchase_date__lte=last_day_of_year
        ).aggregate(total_cost=Sum("purchase__purchase_cost"))["total_cost"] or 0
        

        # last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
        last_day = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        print("last day",last_day)
        # maintenance_cost = Hardware.objects.filter(
        #     services__next_service_date__gte=first_day,
        #     services__next_service_date__lte=last_day            
        # ).aggregate(
        #     total_cost=Sum("services__service_cost")
        # )["total_cost"] or 0
        maintenance_cost = Hardware.objects.filter(
            services__next_service_date__gte=first_day_of_year,
            services__next_service_date__lte=last_day_of_year
        ).aggregate(
            total_cost=Sum("services__service_cost")
        )["total_cost"] or 0

        # maintenance_cost = HardwareService.objects.filter(
        #     next_service_date__gte=first_day,
        #     next_service_date__lte=last_day
        # ).aggregate(
        #     total_cost=Sum("service_cost")
        # )["total_cost"] or 0
        print("purchase cost",purchase_cost,"maintanace cost", maintenance_cost)
        #  Final hardware cost including maintenance
        total_hardware_cost = purchase_cost + maintenance_cost
        # total_hardware_cost = Hardware.objects.filter(is_deleted=False).aggregate(total_cost=Sum("purchase__purchase_cost"))["total_cost"] or 0

        # Subscription Warnings (Renewal in next 7 days)
        renewal_subscriptions = Subscription.objects.filter(next_payment_date__range=[today, next_week]).count()

        # Hardware Warnings
        # warranty_expiring = Hardware.objects.filter(is_deleted=False, warranty__warranty_expiry_date__lte=now() + timedelta(days=30)).count()
        warranty_expiring = Hardware.objects.filter(is_deleted=False,warranty__status="Expiring Soon").count()
        # maintenance_due = Hardware.objects.filter(status="maintenance_due", is_deleted=False).count()
        # maintenance_due = Hardware.objects.filter(is_deleted=False,services__next_service_date__range=[today, today + timedelta(days=7)]).distinct().count()
        maintenance_due = Hardware.objects.filter(is_deleted=False,services__status__in='Maintenance Soon').distinct().count()
        print(maintenance_due)
        # out_of_warranty = Hardware.objects.filter(is_deleted=False, warranty__warranty_expiry_date__lte=now()).count()

        # Total Warnings Count
        total_warnings = renewal_subscriptions + warranty_expiring + maintenance_due 
        total_resources=Resource.objects.filter(status="Active",is_deleted=False).count()
        print("total_resources",total_resources)

        return Response({
            "total_active_subscriptions": active_count,
            "total_active_customers": total_active_customers,
            "total_active_hardware": total_active_hardware,
            "total_hardware":total_hardware,
            "expired_count": expired_count,

            "total_subscription_cost": total_subscription_cost,
            "hardware_cost": total_hardware_cost,
            "renewal_subscriptions": renewal_subscriptions,
            "warranty_expiring": warranty_expiring,
            "maintenance_due": maintenance_due,
            "total_warnings": total_warnings,
            "total_resources": total_resources
            
        })

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Fetch notifications related to the user's subscriptions"""
        return Notification.objects.filter(subscription__admin=self.request.user).order_by("-created_at")

class MarkNotificationAsReadView(generics.UpdateAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        """Mark a specific notification as read."""
        try:
            notification = Notification.objects.get(id=pk, subscription__admin=request.user)
            notification.is_read = True
            notification.save()
            return Response({"message": "Notification marked as read"})
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found"}, status=404)

def cancel_scheduled_tasks(reminder):
    """Cancel scheduled Celery tasks for a reminder."""
    if reminder.scheduled_task_id:
        task_ids = reminder.scheduled_task_id.split(",")  # Split comma-separated task IDs
        for task_id in task_ids:
            try:
                # Revoke the task
                SubSync.control.revoke(task_id, terminate=True)
                logger.info(f"Cancelled task with ID: {task_id}")
            except Exception as e:
                logger.error(f"Failed to cancel task with ID: {task_id}: {e}")

        # Clear the scheduled_task_id field
        reminder.scheduled_task_id = None
        reminder.save()

class ServerListByHostingTypeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]  # Ensure authentication

    def get(self, request):
        hosting_type = request.query_params.get('type')

        if not hosting_type:
            return Response({"error": "hosting_type is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch server names based on hosting_type
        if hosting_type.lower() == "on-premise":
            # servers = Computer.objects.values_list('hardware_server_name', flat=True)
            servers = Computer.objects.filter(computer_type="Server",hardware__is_deleted=False).values_list('hardware_server_name', flat=True)
            print(servers)

        elif hosting_type.lower() == "external":
            servers = Servers.objects.filter(server_type="External",subscription__is_deleted=False).values_list('server_name', flat=True)
            print(servers)

        # elif hosting_type.lower() == "cloud":
        #     servers = Servers.objects.filter(server_type="Cloud",subscription__is_deleted=False).values_list('server_name', flat=True)
        #     print(servers)

        else:
            return Response(
                {"error": "Invalid hosting_type. Choose 'on premise server', 'external', or 'cloud'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"servers": list(servers)}, status=status.HTTP_200_OK)
    
class CustomerAPIView(APIView):
    permission_classes=[IsAuthenticated]

    def post(self, request):
        print(f"🔍 Received request data: {request.data}") 
        # serializer = CustomerSerializer(data=request.data)
        data = request.data.copy()  # Make a mutable copy
        data['user'] = request.user.id  # Assign authenticated user
        data['status'] = "Active"

        # 🔍 Check for duplicates based on name & email
        existing_customer = Customer.objects.filter(
            customer_name=data['customer_name'], email=data['customer_email']
        ).first()

        if existing_customer:
            return Response(
                {"message": "Customer already exists!", "customer_id": existing_customer.id},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # resource_id = request.data.get('resource_name', [])
        
        serializer = CustomerSerializer(data=data)

        if serializer.is_valid():
            customer = serializer.save()
            print(f" Customer saved successfully: {customer}")
            return Response({"message": "Customer added successfully",
                            # "customer": serializer.data
                            "customer": CustomerSerializer(customer).data,"status":status.HTTP_201_CREATED}, status=status.HTTP_201_CREATED)
        
        print(f" Validation failed: {serializer.errors}") 
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        # if not serializer.is_valid():
        #     print(f" Validation failed: {serializer.errors}") 
        #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # try:
        #     with transaction.atomic():
        #         # Create customer
        #         customer = serializer.save()
        #         print(f" Customer saved successfully: {customer}")
        #         reminder = Reminder.objects.create(
        #             reminder_days_before=7,
        #             reminder_months_before=1,
        #             reminder_day_of_month=1,
        #             # optional_days_before=reminder_data.get("optional_days_before"),
        #             notification_method="both",
        #             recipients=request.user.email,
        #             custom_message="Your subscription is about to expire. Please renew it.",
        #             reminder_type="customer expiry",
        #         )

        #         ReminderCustomer.objects.create(reminder=reminder, customer=customer)

        #         reminder_dates = reminder.calculate_all_reminder_dates(customer)
        #         print("Reminder Dates:", reminder_dates)

        #         if reminder_dates:
        #             reminder.reminder_date = reminder_dates[0]
        #             reminder.save()
        #             print("Reminder Date Saved:", reminder.reminder_date)

        #     return Response({
        #         "message": "Customer added successfully",
        #         "customer": CustomerSerializer(customer).data,
        #         "status": status.HTTP_201_CREATED
        #     }, status=status.HTTP_201_CREATED)

        # except Exception as e:
        #     print(f" Error in customer creation: {str(e)}")
        #     return Response(
        #         {"message": "Failed to create customer", "error": str(e)},
        #         status=status.HTTP_500_INTERNAL_SERVER_ERROR
        #     )
    
class ServerUsageView(APIView):
    def get(self, request):
        # servers =Servers.objects.filter(subscription__is_deleted=False)
        # serializer = ServerUsageSerializer(servers, many=True)

        # Fetch cloud servers from Servers model (excluding deleted subscriptions)
        cloud_servers = Servers.objects.filter(subscription__is_deleted=False)
        
        # Fetch on-premise servers from Computer model where type is "server"
        on_prem_servers = Computer.objects.filter(computer_type='Server', hardware__is_deleted=False)

        cloud_serializer = ServerUsageSerializer(cloud_servers, many=True)
        # on_prem_serializer = OnPremServerUsageSerializer(on_prem_servers, many=True)
        print("On-Prem Servers:", on_prem_servers)

        combined_data = cloud_serializer.data
        # + on_prem_serializer.data        

        # data = serializer.data
        for server in combined_data:
            if server['used'] > server['total']:
                server['used'] = server['total']  # Cap used to total
                server['percentage'] = 100  # Ensure percentage does not exceed 100%
            
            print(f"Server: {server['server_name']}, Used: {server['used']}, Total: {server['total']}, Percentage: {server['percentage']}")

        return Response(combined_data, status=status.HTTP_200_OK)
    
#  API to List All Customers
class CustomerListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.prefetch_related('resources').filter(is_deleted=False)
    serializer_class = CustomerSerializer

#  API to Retrieve, Update, or Delete a Customer
class CustomerDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer

    def retrieve(self, request, *args, **kwargs):
        """Retrieve customer details."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "Customer retrieved successfully!", "customer": serializer.data},
            status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        """Update customer details."""
        partial = kwargs.pop('partial', False)  # Handle both PATCH & PUT
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Customer updated successfully!", "status":status.HTTP_200_OK,"customer": serializer.data},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {"message": "Validation failed!", "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, *args, **kwargs):
        """Delete customer (soft delete if applicable)."""
        instance = self.get_object()
        instance.soft_delete(deleted_by=request.user)
        return Response(
            {"message": "Customer deleted successfully!","status":status.HTTP_200_OK},
            status=status.HTTP_200_OK
        )

#  List All Resources or Create a New Resource
class ResourceListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    # queryset = Resource.objects.all()
    queryset = Resource.objects.filter(is_deleted=False)
    serializer_class = ResourceViewSerializer

    # def list(self, request, *args, **kwargs):
    #     queryset = self.get_queryset()
    #     serializer = self.get_serializer(queryset, many=True)

    #     return Response(
    #         {
    #             "message": "Resource list retrieved successfully!",
    #             "count": queryset.count(),
    #             "resources": serializer.data,
    #             "status": status.HTTP_200_OK
    #         },
    #         status=status.HTTP_200_OK
    #     )

# Retrieve, Update, or Delete a Specific Resource
class ResourceDetailUpdateView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Resource.objects.filter(is_deleted=False)
    serializer_class = ResourceViewSerializer

    def retrieve(self, request, *args, **kwargs):
        """Custom response for retrieving a single resource."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {
                "message": "Resource retrieved successfully!",
                "resource": serializer.data,
                "status": status.HTTP_200_OK
            },
            status=status.HTTP_200_OK
        )

    def update(self, request, *args, **kwargs):
        """Custom response for updating a resource."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "Resource updated successfully!",
                    "resource": serializer.data,
                    "status": status.HTTP_200_OK
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {
                "message": "Resource update failed!",
                "errors": serializer.errors,
                "status": status.HTTP_400_BAD_REQUEST
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    def destroy(self, request, *args, **kwargs):
        """Custom response for deleting a resource."""
        instance = self.get_object()
        instance.soft_delete(deleted_by=request.user)
        return Response(
            {
                "message": "Resource deleted successfully!",
                "status": status.HTTP_200_OK
            },
            status=status.HTTP_200_OK
        )

class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        # Extract the refresh token from request
        refresh_token = request.data.get('refresh')
        # logger.debug(f"Received refresh token: {refresh_token}")
        print(f"Received refresh token: {refresh_token}")

        # Call the parent method to process the request
        response = super().post(request, *args, **kwargs)

        # Log and print the response data
        # logger.debug(f"Response data: {response.data}")
        print(f"Response data: {response.data}")

        # return response
        if response.status_code == 200 and 'access' in response.data:
            # return Response(
            #     {
            #         "message": "Refreshed token",
            #         "data": response.data,
            #         "status": response.status_code,
            #         "access": response.data['access']
            #     },
            #     status=status.HTTP_200_OK
            # )
            return Response(response.data, status=response.status_code)
        else:
            return response

class CustomerTypePercentageAPIView(APIView):
    def get(self, request):
        # Get total customers
        total_customers = Customer.objects.count()

        if total_customers == 0:
            return Response({"error": "No customers found"}, status=status.HTTP_404_NOT_FOUND)

        # Count customers by type
        inhouse_count = Customer.objects.filter(customer_type="inhouse").count()
        print(f"in house count {inhouse_count}")
        external_count = Customer.objects.filter(customer_type="external").count()
        print(f"external count {external_count}")

        # Calculate percentages
        inhouse_percentage = (inhouse_count / total_customers) * 100
        external_percentage = (external_count / total_customers) * 100

        # Prepare response data
        data = [
            {"name": "Inhouse", "value": round(inhouse_percentage, 2)},
            {"name": "External", "value": round(external_percentage, 2)}
        ]

        return Response(data, status=status.HTTP_200_OK)

class ServerReportAPIView(APIView):
    def get(self, request):
        # servers = Servers.objects.all()
        servers = Servers.objects.all().prefetch_related('server_resources')
        data = []

        for server in servers:
            usage_serializer = ServerUsageSerializer(server)  # Get computed values
            used_capacity = usage_serializer.data["used"]
            total_capacity = usage_serializer.data["total"]
            # remaining_capacity = total_capacity - used_capacity
            remaining_capacity = max(total_capacity - used_capacity, 0)
            usage_percentage = usage_serializer.data["percentage"]

            server_data = {
                "id": server.id,
                "server_name": server.server_name,
                "server_type": server.server_type,
                "server_capacity": server.server_capacity,
                "used_capacity": f"{used_capacity}GB",
                "remaining_capacity": f"{remaining_capacity}GB",
                "usage_percentage": f"{usage_percentage}%",
                # "usage_percentage": f"{usage_percentage:.2f}%",
                # "usage_percentage_value": usage_percentage,
                # "usage_percentage_value": float(usage_percentage),
                "resources": [
                    {
                        "resource_name": resource.resource_name,
                        "resource_type": resource.resource_type,
                        "storage_capacity": resource.storage_capacity,
                        # "used_storage": resource.used_storage,
                        # "remaining_storage": resource.remaining_storage,
                        "billing_cycle": resource.billing_cycle,
                        # "resource_cost": resource.resource_cost,
                        "resource_cost": float(resource.resource_cost) if resource.resource_cost else 0,
                        # "next_payment_date": resource.next_payment_date,
                        "next_payment_date": resource.next_payment_date.strftime("%Y-%m-%d") if resource.next_payment_date else None,
                        # "provisioned_date": resource.provisioned_date,
                        "provisioned_date": resource.provisioned_date.strftime("%Y-%m-%d") if resource.provisioned_date else None,
                        # "last_updated_date": resource.last_updated_date,
                        "last_payement_date": resource.last_payment_date.strftime("%Y-%m-%d") if resource.last_payment_date else None,
                        "status": resource.status,
                        "hosting_type": resource.hosting_type,
                        # "hosting_location": resource.hosting_location
                    }
                    for resource in server.server_resources.all()
                ]
            }
            data.append(server_data)

        return Response(data)

class SubscriptionSoftDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, subscription_id):
        try:
            subscription = Subscription.objects.get(id=subscription_id, is_deleted=False)

            subscription.soft_delete(deleted_by=request.user)

            return Response({"message": "Subscription deleted successfully.","status":status.HTTP_200_OK}, status=status.HTTP_200_OK)
        
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found or already deleted."}, status=status.HTTP_404_NOT_FOUND)

class RecycleBinView(APIView):
    def get(self, request):
        """
        Fetch all soft-deleted items that have 30 days or less before permanent deletion.
        Transform the data into the frontend format.
        """
        # Calculate the date 30 days from now
        thirty_days_from_now = timezone.now() + timedelta(days=30)

        # Fetch soft-deleted items with deletion dates within the next 30 days
        subscriptions = Subscription.objects.filter(
            is_deleted=True,
            deleted_at__lte=thirty_days_from_now
        )
        hardware = Hardware.objects.filter(
            is_deleted=True,
            deleted_at__lte=thirty_days_from_now
        )
        customers = Customer.objects.filter(
            is_deleted=True,
            deleted_at__lte=thirty_days_from_now
        )

        # Serialize the data
        subscription_data = SubscriptionDetailSerializer(subscriptions, many=True).data
        print(subscription_data)
        hardware_data = HardwareSerializer(hardware, many=True).data
        print(hardware_data)
        customer_data = CustomerSerializer(customers, many=True).data
        print(customer_data)

        # Transform the data into the frontend format
        transformed_data = self.transform_to_frontend_format(
            subscription_data, hardware_data, customer_data
        )
        print(transformed_data)

        return Response(transformed_data, status=status.HTTP_200_OK)

    def transform_to_frontend_format(self, subscription_data, hardware_data, customer_data):
        """
        Transform backend data into the frontend format.
        """
        transformed_data = []
        current_date = timezone.now()

        # Transform subscriptions
        for subscription in subscription_data:
            deleted_at_str = subscription.get("deleted_at")
            # print(deleted_at_str)
            if deleted_at_str:
                deleted_at = datetime.fromisoformat(deleted_at_str)
                # Calculate expiration date (30 days after deletion)
                expiration_date = deleted_at + timedelta(days=30)
                # Calculate remaining days
                remaining_days = (expiration_date - current_date).days
            else:
                remaining_days = None  

            transformed_data.append({
                "id":subscription['id'],
                "name": subscription.get("name", "Unnamed Subscription"),
                "type": "subscription",
                "deletedAt": deleted_at_str,
                "deletedBy": subscription.get("deleted_by_username", "Unknown"),
                "expiresAt": remaining_days,
            })

        # Transform hardware
        for hardware in hardware_data:
            deleted_at_str = hardware.get("deleted_at")
            if deleted_at_str:
                deleted_at = datetime.fromisoformat(deleted_at_str)
                expiration_date = deleted_at + timedelta(days=30)
                remaining_days = (expiration_date - current_date).days
            else:
                remaining_days = None
            transformed_data.append({
                "id": hardware['id'],
                # "name": hardware.get("name", "Unnamed Hardware"),
                "type": "hardware",
                "deletedAt": deleted_at_str,
                "deletedBy": hardware.get("deleted_by_username", "Unknown"),
                "expiresAt": remaining_days,
            })

        # Transform customers
        for customer in customer_data:
            deleted_at_str = customer.get("deleted_at")
            if deleted_at_str:
                deleted_at = datetime.fromisoformat(deleted_at_str)
                expiration_date = deleted_at + timedelta(days=30)
                remaining_days = (expiration_date - current_date).days
            else:
                remaining_days = None

            transformed_data.append({
                "id": customer['id'],
                "name": customer.get("customer_name", "Unnamed Customer"),
                "type": "customer",
                "deletedAt": deleted_at_str,
                "deletedBy": customer.get("deleted_by_username", "Unknown"),
                "expiresAt": remaining_days,
            })

        return transformed_data

    def post(self, request):
        """
        Restore soft-deleted items or permanently delete selected items.
        Handles multiple operations in a single request.
        """
        if not isinstance(request.data, list):
            return Response({'error': 'Expected an array of operations'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        
        for operation in request.data:
            action = operation.get('action')  # 'restore' or 'delete_permanently'
            item_type = operation.get('type')  # 'subscription', 'hardware', or 'customer'
            item_ids = operation.get('ids', [])  # List of item IDs to restore or delete

            if action not in ['restore', 'delete']:
                results.append({
                    'status': 'error',
                    'message': 'Invalid action',
                    'operation': operation
                })
                continue
                # return Response({'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)

            if item_type not in ['subscription', 'hardware', 'customer']:
                results.append({
                    'status': 'error',
                    'message': 'Invalid item type',
                    'operation': operation
                })
                continue
                # return Response({'error': 'Invalid item type'}, status=status.HTTP_400_BAD_REQUEST)

            if not item_ids:
                results.append({
                    'status': 'error',
                    'message': 'No items selected',
                    'operation': operation
                })
                continue
                # return Response({'error': 'No items selected'}, status=status.HTTP_400_BAD_REQUEST)

            # Fetch the items based on the type
            if item_type == 'subscription':
                items = Subscription.objects.filter(id__in=item_ids, is_deleted=True)
            elif item_type == 'hardware':
                items = Hardware.objects.filter(id__in=item_ids, is_deleted=True)
            elif item_type == 'customer':
                items = Customer.objects.filter(id__in=item_ids, is_deleted=True)

            if not items.exists():
                results.append({
                    'status': 'error',
                    'message': 'No matching items found',
                    'operation': operation
                })
                continue
                # return Response({'error': 'No matching items found'}, status=status.HTTP_404_NOT_FOUND)

            # Perform the action
            try:
                if action == 'restore':
                    for item in items:
                        item.restore()  # Call the restore method
                    message = f'{len(items)} {item_type}(s) restored successfully'
                elif action == 'delete':
                    items.delete()  # Permanently delete the items
                    message = f'{len(items)} {item_type}(s) permanently deleted'

                results.append({
                    'status': 'success',
                    'message': message,
                    'operation': operation,
                    'count': len(items)
                })
            except Exception as e:
                results.append({
                    'status': 'error',
                    'message': str(e),
                    'operation': operation
                })

        # Check if all operations were successful
        all_success = all(result['status'] == 'success' for result in results)
        status_code = status.HTTP_200_OK if all_success else status.HTTP_207_MULTI_STATUS

        return Response({'results': results,'status':status_code}, status=status_code)

    # def delete(self, request):
    #     """
    #     Automatically delete items that have been in the recycle bin for more than 30 days.
    #     """
    #     # Calculate the date 30 days ago
    #     thirty_days_ago = timezone.now() - timedelta(days=30)

    #     # Fetch items that were deleted more than 30 days ago
    #     Subscription.objects.filter(is_deleted=True, deleted_at__lte=thirty_days_ago).delete()
    #     Hardware.objects.filter(is_deleted=True, deleted_at__lte=thirty_days_ago).delete()
    #     Customer.objects.filter(is_deleted=True, deleted_at__lte=thirty_days_ago).delete()

    #     return Response({'message': 'Old items permanently deleted'}, status=status.HTTP_200_OK)

class IsSuperUserCheckAPIView(APIView):
    """
    API endpoint to check if the authenticated user is a superuser.
    """
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def get(self, request, *args, **kwargs):
        """
        Check if the authenticated user is a superuser.
        """
        user = request.user
        is_superuser = user.is_superuser  # Check if the user is a superuser

        return Response({
            "is_superuser": is_superuser,
            "username": user.username,
            "email": user.email,
        }, status=status.HTTP_200_OK)
    
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Support pagination if configured
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                "status": "success",
                "message": "Users retrieved successfully",
                "data": serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            "status": "success",
            "message": "Users retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class UserStatusUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserStatusUpdateSerializer
    permission_classes = [IsAuthenticated]  # Only authenticated users can update

    def update(self, request, *args, **kwargs):
        user_id = kwargs.get('pk')  # Get user ID from URL
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"status": "error", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "status": status.HTTP_200_OK,
                "message": "User status updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class YearlyHardwareCostBreakdownAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        hardware_list = Hardware.objects.filter(is_deleted=False)

        year_wise_data = defaultdict(lambda: {
            "total_purchase_cost": 0,
            "total_maintenance_cost": 0,
            "total_hardware_cost": 0,
            "hardware_cost_breakdown": []
        })

        for hardware in hardware_list:
            # ----- Handle Purchase -----
            if hasattr(hardware, 'purchase') and hardware.purchase.purchase_date:
                purchase_year = hardware.purchase.purchase_date.year
                purchase_cost = hardware.purchase.purchase_cost or 0

                year_wise_data[purchase_year]["total_purchase_cost"] += purchase_cost
                year_wise_data[purchase_year]["total_hardware_cost"] += purchase_cost
                year_wise_data[purchase_year]["hardware_cost_breakdown"].append({
                    "hardware_id": hardware.id,
                    "hardware_type": hardware.hardware_type,
                    "serial_number": hardware.serial_number,
                    "manufacturer": hardware.manufacturer,
                    "model_number": hardware.model_number,
                    "purchase_cost": purchase_cost,
                    "maintenance_cost": 0,
                    "total_cost": purchase_cost,
                })

            # ----- Handle Maintenance -----
            service = hardware.services
            # for service in maintenance_services:
            if service.last_service_date:
                service_year = service.last_service_date.year
                service_cost = service.service_cost or 0

                year_wise_data[service_year]["total_maintenance_cost"] += service_cost
                year_wise_data[service_year]["total_hardware_cost"] += service_cost

                # Try to match existing entry for same hardware in that year
                found = False
                for item in year_wise_data[service_year]["hardware_cost_breakdown"]:
                    if item["hardware_id"] == hardware.id:
                        item["maintenance_cost"] += service_cost
                        item["total_cost"] += service_cost
                        found = True
                        break

                if not found:
                    year_wise_data[service_year]["hardware_cost_breakdown"].append({
                        "hardware_id": hardware.id,
                        "hardware_type": hardware.hardware_type,
                        "serial_number": hardware.serial_number,
                        "manufacturer": hardware.manufacturer,
                        "model_number": hardware.model_number,
                        "purchase_cost": 0,
                        "maintenance_cost": service_cost,
                        "total_cost": service_cost,
                    })

        return Response(year_wise_data)

class ProviderDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Provider.objects.filter(is_deleted=False)
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.soft_delete(deleted_by=request.user)  # Soft delete with user
        return Response({"detail": "Provider deleted successfully."}, status=status.HTTP_204_NO_CONTENT)

class SubscriptionHistoryView(generics.ListAPIView):
    serializer_class = SubscriptionHistorySerializer
    
    def get_queryset(self):
        subscription_id = self.kwargs['pk']
        return Subscription.history.filter(id=subscription_id).select_related('history_user')

class NotificationListAPI(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

class MarkNotificationReadAPI(generics.UpdateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_update(self, serializer):
        serializer.save(is_read=True)