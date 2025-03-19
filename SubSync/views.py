import os
from django.contrib.auth import authenticate
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import AllowAny

User = get_user_model()

# @method_decorator(csrf_exempt, name='dispatch')
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
                'message': 'Invalid email or password. Please try again.',
                'status': status.HTTP_401_UNAUTHORIZED
                
                , 'error': 'Invalid email or password'
                },
                  status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Login successful',
            'token': str(refresh.access_token),
            'refresh': str(refresh),
            'status': status.HTTP_200_OK,
        }, status=status.HTTP_200_OK)


from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        print("email:",email)

        if not email:
            return Response({"error": "Email is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Always return a generic message to avoid email enumeration
            return Response({
                "message": "If an account with this email exists, you will receive a password reset email shortly."
            }, status=status.HTTP_200_OK)
        
        token_generator = PasswordResetTokenGenerator()
        token = token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # reset_url = f"{request.build_absolute_uri('/api/reset-password/')}?uid={uidb64}&token={token}"
        # frontend_url = settings.FRONTEND_URL  # Example: "https://myfrontend.com"
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
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        
        return Response({
            "message": "If an account with this email exists, you will receive a password reset email shortly.",
            'status': status.HTTP_200_OK,
        }, status=status.HTTP_200_OK)

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .serializers import HardwareSerializer, PasswordResetSerializer, SubscriptionDetailSerializer, SubscriptionWarningSerializer

User = get_user_model()

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
                return Response({"error": "Invalid uid."}, status=status.HTTP_400_BAD_REQUEST)
            
            token_generator = PasswordResetTokenGenerator()
            if not token_generator.check_token(user, token):
                return Response({"error": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)
            
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password reset successful",
                             'status': status.HTTP_200_OK,}, status=status.HTTP_200_OK)
        
        else:
            print("Reset Password Error:", serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]  # Only logged-in users can change their password

    def post(self, request):
        user = request.user  # Get the currently logged-in user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        # Check if old password is correct
        if not user.check_password(old_password):
            return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate new password (checks Django password validators)
        try:
            validate_password(new_password, user)
        except ValidationError as e:
            return Response({"error": e.messages}, status=status.HTTP_400_BAD_REQUEST)

        # Update password
        user.set_password(new_password)
        user.save()

        return Response({"message": "Password updated successfully",
                         'status': status.HTTP_200_OK,}, status=status.HTTP_200_OK)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class CreateUserAPIView(APIView):
    permission_classes = [AllowAny] 

    def post(self, request):
        email = request.data.get("email")
        username = request.data.get("username")
        password = request.data.get("password")

        if not email or not username or not password:
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(email=email, username=username, password=password)
        return Response({"message": "User created successfully"}, status=status.HTTP_201_CREATED)


from django.db.models import Count
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from SubSync.models import Subscription, Hardware 

class DashboardOverview(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        total_active_subscriptions = Subscription.objects.filter(status="Active").count()
        total_hardware_items = Hardware.objects.count()
        total_active_customers = Customer.objects.filter(status="Active").count()

        return Response({
            "total_active_subscriptions": total_active_subscriptions,
            "total_hardware_items": total_hardware_items,
            "total_active_customers": total_active_customers
        })

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import UserProfileSerializer

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """View user profile."""
        user = request.user
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        """Update user profile."""
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Customer, Subscription

class SubscriptionCountView(APIView):
    """Fetch the count of active and expired subscriptions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        active_count = Subscription.objects.filter(end_date__gte=now()).count()
        expired_count = Subscription.objects.filter(end_date__lt=now()).count()

        return Response({
            "total_active_subscriptions": active_count,
            "total_expired_subscriptions": expired_count,
            'status': status.HTTP_200_OK,
        })

from django.utils.timezone import now
from datetime import timedelta
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Subscription
from .serializers import SubscriptionSerializer

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
            Subscription.objects.filter(next_payment_date__range=[today, next_week])
            .select_related(
                "provider", "billing", "software_detail", "domain", "server"
            )  # Optimized DB queries
        )

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from .models import Subscription

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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models.functions import TruncMonth
from django.db.models import Count
from .models import Subscription
import calendar

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

from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from .models import Hardware, Provider
from .serializers import ProviderSerializer
from rest_framework.permissions import AllowAny

class ProviderCreateView(generics.CreateAPIView):
    queryset = Provider.objects.all()
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        print("Request Data:", request.data)
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(
                { "status": status.HTTP_201_CREATED},
                status=status.HTTP_201_CREATED
            )
        
        # logger.error(f"Validation Error: {serializer.errors}")
        # print("Validation Errors:", serializer.errors)  # Debugging

        return Response(
            {"status": "error", "code": status.HTTP_400_BAD_REQUEST, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
from rest_framework import generics
from .models import Provider
from .serializers import ProviderSerializer
from rest_framework.permissions import AllowAny

class ProviderListView(generics.ListAPIView):
    # queryset = Provider.objects.all()
    queryset = Provider.objects.all().only("id", "provider_name")
    serializer_class = ProviderSerializer
    permission_classes = [IsAuthenticated]  # Ensure anyone can access it

    def get_queryset(self):
        queryset = Provider.objects.only("id", "provider_name")
        print("\n*************************************************************************************************************************************")
        print("Providers List:", list(queryset.values("id", "provider_name")))  # Print all providers
        print("\n************************************************************************************************************************************")
        return queryset

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from SubSync.models import Subscription

class SubscriptionChoicesView(APIView):
    permission_classes = [AllowAny]  # Allow public access

    def get(self, request, *args, **kwargs):
        choices = {
            "category_choices": Subscription.CATEGORY_CHOICES,
            # "payment_status_choices": Subscription.PAYMENT_STATUS_CHOICES,
            # "status_choices": Subscription.STATUS_CHOICES,
        }
        return Response(choices)

from rest_framework import generics,filters
from rest_framework.response import Response
from rest_framework import status
from .models import Subscription, Provider
from .serializers import SubscriptionSerializer
from rest_framework import permissions
from .models import SoftwareSubscriptions, Utilities, Domain, Servers
from django.core.exceptions import ValidationError
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import ReminderSubscription

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
            # "paymentStatus": "payment_status",
            "status": "status",
            # "subscriptionId": "subscription_id",
            "startDate": "start_date",
            "endDate": "end_date",
            "paymentMethod": "payment_method",
            "notificationMethod":"notification_method",
            # "nextPaymentDate":"next_payment_date",
            "customMessage":"custom_message",
            "billingCycle":"subscription_cycle",
            
            "daysBeforeEnd":"optional_days_before",
            "firstReminderMonth":"reminder_months_before",
            "reminderDay":"reminder_days_before",

            # "lastPaymentDate":"last_payment_date",
            # "providerContact":"contact_phone",
            # "providerEmail":"contact_email",
            # "providerName":"provider_name",
            # "websiteLink":"website",
            # "userId": "user"  # Ensure user ID is included
        }

        for frontend_key, backend_key in field_mapping.items():
            if frontend_key in data:
                value = data.pop(frontend_key)
                # Convert empty string to None for integer fields
                if backend_key in ["optional_days_before", "reminder_months_before", "reminder_days_before"] and value == "":
                    data[backend_key] = None  # or use 0 if needed
                else:
                    data[backend_key] = value

        print("Modified Data:", data)
        print("\n***********************************************************************************************************************************")
        # ✅ Set 'status' dynamically
        data["status"] = "Active"
        data["reminder_type"] = "renewal"
        data["payment_status"] = "Paid"
        # data["reminder_time"] = "14:45:00"
        data["reminder_status"] = "pending"
        # ✅ Assign 'user' field (assuming user is the logged-in user)
        data["user"] = request.user.id
        # data["created_by"] = request.user.id
        print("Final Data Before Saving:", data)
        print("\n***********************************************************************************************************************************")

        provider_id = data.get("providerid")  # Get provider ID from request
        print("🔍 Selected Provider ID:", provider_id)

        if not provider_id:
            return Response({"error": "Provider ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the provider instance from DB
        try:
            provider = Provider.objects.get(id=provider_id)
        except Provider.DoesNotExist:
            return Response({"error": "Invalid Provider ID."}, status=status.HTTP_400_BAD_REQUEST)

        # Assign provider to subscription data
        data["provider"] = provider.id

        # Extract additional fields separately
        additional_fields = data.pop("additionalDetails", {})

        # Extract and remove reminder-related fields before subscription creation
        reminder_fields = [
            "reminder_type", "subscription_cycle", "reminder_days_before",
            "reminder_months_before", "reminder_day_of_month",
            "notification_method", "recipients", "custom_message", "optional_days_before"
        ]
        reminder_data = {key: data.pop(key) for key in reminder_fields if key in data}

        # ✅ Apply default reminder settings if none provided
        if not any(reminder_data.values()):
            subscription_cycle = data.get("subscription_cycle", "monthly")

            if subscription_cycle in ["weekly", "monthly"]:
                reminder_data["reminder_days_before"] = 7  # Default to 7 days before due date
            else:
                reminder_data["reminder_months_before"] = 1  # Default to 1 month before
                reminder_data["reminder_day_of_month"] = 1  # Default to 1st day of the month

            reminder_data["notification_method"] = "email"  # Default notification method
            reminder_data["reminder_type"] = "renewal"  # Default reminder type
            reminder_data["reminder_status"] = "pending"
            reminder_data["recipients"] = request.user.email  # Default to user's email
            reminder_data["custom_message"] = "Your subscription is due soon. Please renew it in time."  # Default message

        # Validate and create subscription
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            subscription = serializer.save()

            # Handle category-specific data
            category = subscription.subscription_category
            if category == "Software":
                SoftwareSubscriptions.objects.create(subscription=subscription, **additional_fields)
            elif category == "Billing":
                utility_instance = Utilities(subscription=subscription, **additional_fields)
                try:
                    utility_instance.clean()
                    utility_instance.save()
                except ValidationError as e:
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            elif category == "Domain":
                Domain.objects.create(subscription=subscription, **additional_fields)
            elif category == "Server":
                Servers.objects.create(subscription=subscription, **additional_fields)

            # Create the reminder entry if reminder data exists
            if reminder_data:
                subscription_cycle = reminder_data.get("subscription_cycle")

                # Validate reminder fields based on subscription cycle
                if subscription_cycle in ["weekly", "monthly"]:
                    reminder_days_before = reminder_data.get("reminder_days_before")
                    print("Reminder Days Before:", reminder_days_before)

                    if reminder_days_before is None or reminder_days_before == "":
                        return Response(
                            {"error": "reminder_days_before is required for weekly/monthly cycles."},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    # Remove unnecessary fields
                    reminder_data.pop("reminder_months_before", None)
                    reminder_data.pop("reminder_day_of_month", None)
                else: # Long-term cycles (e.g., yearly, custom)
                    reminder_months_before = reminder_data.get("reminder_months_before")
                    reminder_day_of_month = reminder_data.get("reminder_day_of_month")
                    
                    if subscription_cycle not in ["weekly", "monthly"] and (not reminder_months_before or not reminder_day_of_month):

                        return Response(
                            {"error": "reminder_months_before and reminder_day_of_month are required for long-term cycles."},
                            status=status.HTTP_400_BAD_REQUEST
                        )

            if reminder_data:
                # Create Reminder
                reminder = Reminder.objects.create(
                    subscription_cycle=subscription_cycle,
                    reminder_days_before=reminder_data.get("reminder_days_before"),
                    reminder_months_before=reminder_data.get("reminder_months_before"),
                    reminder_day_of_month=reminder_data.get("reminder_day_of_month"),
                    optional_days_before=reminder_data.get("optional_days_before"),
                    notification_method=reminder_data.get("notification_method"),
                    recipients=reminder_data.get("recipients"),
                    custom_message=reminder_data.get("custom_message"),
                    reminder_type=reminder_data.get("reminder_type"),
                )

                # Link the reminder with the subscription
                ReminderSubscription.objects.create(reminder=reminder, subscription=subscription)

                # Calculate and save the reminder_date
                reminder_dates = reminder.calculate_all_reminder_dates(subscription)
                print("Reminder Dates:", reminder_dates)

                if reminder_dates:
                    print("First Reminder Date:", reminder_dates[0])
                else:
                    print("❌ No Reminder Dates Generated!")
                    return Response({"error": "Reminder dates could not be generated."}, status=status.HTTP_400_BAD_REQUEST)

            if reminder_dates:
                reminder.reminder_date = reminder_dates[0]  # Assign the first reminder date
                reminder.save()
                print("Reminder Date Saved:", reminder.reminder_date)
            
            return Response({'code': status.HTTP_201_CREATED, 'data': serializer.data}, status=status.HTTP_201_CREATED)
        
        if not serializer.is_valid():
            print("Serializer Errors:", serializer.errors)  # Print detailed errors
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# from django.utils import timezone
# from django_filters.rest_framework import DjangoFilterBackend
# from rest_framework import generics, permissions, filters
# from rest_framework.response import Response
# from rest_framework.exceptions import APIException
# from SubSync.models import Subscription  # Adjust based on your app name
# from SubSync.serializers import SubscriptionSerializer,SubscriptionFilterSerializer  # Ensure correct import
# from .filters import SubscriptionFilter
# from SubSync.filters import SubscriptionFilter

# class SubscriptionListView(generics.ListAPIView):
#     """
#     API endpoint to view and filter subscriptions based on category, provider, and status.
#     """
#     queryset = Subscription.objects.all()
#     serializer_class = SubscriptionFilterSerializer
#     permission_classes = [permissions.IsAuthenticated]  # Only admin users can access
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]

#     filterset_class = SubscriptionFilter
    
#     # Filter options
#     filterset_fields = ['subscription_category', 'provider', 'payment_status']

#     # Sorting options
#     ordering_fields = ['provider', 'subscription_category', 'payment_status', 'end_date']
#     # ordering = ['end_date']  # Default sorting by renewal/end date
#     ordering_fields = ["start_date", "end_date", "next_payment_date", "provider"]

#     # Search by subscription name
#     search_fields = ["software_detail__software_name", "server__server_name", "domain__domain_name", "billing__utility_type"]

#     def get_queryset(self):
#         """
#         Filter subscriptions based on status (Active, Expired, Upcoming) and category.
#         """
#         queryset = super().get_queryset()
#         now = timezone.now()

#         # Get filter parameters
#         status_filter = self.request.query_params.get('status', '').strip().lower()
#         category_filter = self.request.query_params.get('subscription_category', '').strip()
#         provider_filter = self.request.query_params.get('provider', '').strip()

#         # Apply status filter
#         if status_filter:
#             if status_filter == 'active':
#                 queryset = queryset.filter(payment_status='paid')
#             elif status_filter == 'expired':
#                 queryset = queryset.filter(end_date__lt=now)  # Use correct field
#             elif status_filter == 'upcoming':
#                 queryset = queryset.filter(end_date__gt=now)

#         # Apply category filter
#         if category_filter:
#             queryset = queryset.filter(subscription_category=category_filter)

#         # Apply provider filter
#         if provider_filter:
#             queryset = queryset.filter(provider=provider_filter)

#         return queryset

#     def list(self, request, *args, **kwargs):
#         """
#         Handle exceptions gracefully, ensuring a proper API response.
#         """
#         try:
#             return super().list(request, *args, **kwargs)
#         except Exception as e:
#             raise APIException(f"An error occurred: {str(e)}")
class SubscriptionListView(generics.ListAPIView):
    """
    API endpoint to view detailed subscription data including related fields.
    """
    # queryset = Subscription.objects.prefetch_related(
    #     "software_detail", "billing", "domain", "server"
    # ).all()
    queryset = Subscription.objects.select_related("provider").prefetch_related(
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

from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from SubSync.models import Subscription
from SubSync.serializers import SubscriptionSerializer

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

from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from SubSync.models import Subscription
from SubSync.serializers import SubscriptionSerializer

class SubscriptionDetailUpdateView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        """Fetch subscription details."""
        try:
            subscription = Subscription.objects.get(pk=pk)
            serializer = SubscriptionSerializer(subscription)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        """Update subscription details."""
        try:
            subscription = Subscription.objects.get(pk=pk)
        except Subscription.DoesNotExist:
            return Response({"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = SubscriptionSerializer(subscription, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Validate: End date should not be before start date
            start_date = serializer.validated_data.get("start_date", subscription.start_date)
            end_date = serializer.validated_data.get("end_date", subscription.end_date)

            if end_date < start_date:
                return Response({"error": "End date cannot be before start date"}, status=status.HTTP_400_BAD_REQUEST)

            serializer.save()
            return Response({"message": "Subscription updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from datetime import datetime, timedelta
import csv
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from SubSync.models import Subscription
from SubSync.serializers import SubscriptionSerializer

# class ExpenditureAnalysisView(APIView):
#     """
#     API View for Monthly Expenditure Analysis.
#     Allows filtering by time range, category, and provider.
#     """

#     permission_classes = [AllowAny]
#     def get(self, request):
#         # Extract filters
#         time_range = request.GET.get("time_range", "current_month")
#         category = request.GET.get("subscription_category", None)
#         provider = request.GET.get("provider", None)
#         export_format = request.GET.get("export", None)  # csv or pdf

#         # Determine start date based on time range
#         today = datetime.today().date()
#         if time_range == "last_3_months":
#             start_date = today - timedelta(days=90)
#         elif time_range == "yearly":
#             start_date = today.replace(month=1, day=1)
#         else:  # Default to current month
#             start_date = today.replace(day=1)

#         # Fetch subscriptions within the date range
#         subscriptions = Subscription.objects.filter(start_date__gte=start_date)

#         # Apply additional filters
#         if category:
#             subscriptions = subscriptions.filter(subscription_category=category)
#         if provider:
#             subscriptions = subscriptions.filter(provider=provider)

#         # Calculate total expenditure
#         total_expenditure = sum(sub.cost for sub in subscriptions)

#         # Prepare response data
#         response_data = {
#             "total_expenditure": total_expenditure,
#             "subscriptions": SubscriptionSerializer(subscriptions, many=True).data,
#         }

#         # Handle export requests
#         if export_format == "csv":
#             return self.export_csv(subscriptions)
#         elif export_format == "pdf":
#             return self.export_pdf(subscriptions)

#         return Response(response_data, status=status.HTTP_200_OK)

#     def export_csv(self, subscriptions):
#         """
#         Exports expenditure data as a CSV file.
#         """
#         response = HttpResponse(content_type="text/csv")
#         response["Content-Disposition"] = 'attachment; filename="expenditure_report.csv"'
#         writer = csv.writer(response)

#         # Write CSV headers
#         writer.writerow(["Subscription Name", "Category", "Cost", "Start Date", "End Date"])

#         # Write data rows
#         for sub in subscriptions:
#             writer.writerow([sub.software_name or sub.server_name or sub.domain_name or sub.utility_name,
#                              sub.subscription_category, sub.cost, sub.start_date, sub.end_date])

#         return response

    # def export_pdf(self, subscriptions):
    #     """
    #     Exports expenditure data as a PDF file.
    #     """
    #     # Implement PDF generation (e.g., using ReportLab)
    #     return Response({"message": "PDF export not implemented yet"}, status=status.HTTP_501_NOT_IMPLEMENTED)

from datetime import datetime, timedelta
from collections import defaultdict
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from SubSync.models import Subscription
from SubSync.serializers import SubscriptionSerializer
from decimal import Decimal

class ExpenditureAnalysisView(APIView):
    """
    API View for Monthly Expenditure Analysis.
    Provides structured data for visualization (line chart, pie chart).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        # Extract filters
        time_range = request.GET.get("time_range", "current_month")
        category = request.GET.get("subscription_category", None)
        provider = request.GET.get("provider", None)
        export_format = request.GET.get("export", None)  # csv or pdf

        # Determine start date based on time range
        today = datetime.today().date()
        if time_range == "last_3_months":
            start_date = today - timedelta(days=90)
        elif time_range == "yearly":
            start_date = today.replace(month=1, day=1)
        else:  # Default to current month
            start_date = today.replace(day=1)

        # Fetch subscriptions within the date range
        subscriptions = Subscription.objects.filter(start_date__gte=start_date)

        # Apply additional filters
        if category:
            subscriptions = subscriptions.filter(subscription_category=category)
        if provider:
            subscriptions = subscriptions.filter(provider=provider)

        # Calculate total expenditure
        total_expenditure = subscriptions.aggregate(Sum("cost"))["cost__sum"] or 0

        # Prepare data for charts
        line_chart_data = self.get_spending_trends(subscriptions)
        pie_chart_data = self.get_category_wise_expenditure(subscriptions)

        # Prepare response data
        response_data = {
            "total_expenditure": total_expenditure,
            "spending_trends": line_chart_data,  # Data for line chart
            "category_breakdown": pie_chart_data,  # Data for pie chart
            "subscriptions": SubscriptionSerializer(subscriptions, many=True).data,
        }

        # Handle export requests
        if export_format == "csv":
            return self.export_csv(subscriptions)
        elif export_format == "pdf":
            return self.export_pdf(subscriptions)

        return Response(response_data, status=status.HTTP_200_OK)

    # def get_spending_trends(self, subscriptions):
    #     """
    #     Aggregates monthly expenditure for line chart.
    #     """
    #     trends = defaultdict(float)

    #     for sub in subscriptions:
    #         month = sub.start_date.strftime("%Y-%m")  # Grouping by YYYY-MM
    #         trends[month] += sub.cost

    #     # Convert to sorted list
    #     return [{"month": key, "expenditure": value} for key, value in sorted(trends.items())]
    def get_spending_trends(self, subscriptions):
        """
        Aggregates monthly expenditure for line chart.
        """
        trends = defaultdict(Decimal)  # Use Decimal instead of float to match sub.cost type

        for sub in subscriptions:
            month = sub.start_date.strftime("%Y-%m")  # Grouping by YYYY-MM
            trends[month] += Decimal(sub.cost)  # Ensure correct type

    # Convert to sorted list with float values for JSON compatibility
        return [{"month": key, "expenditure": float(value)} for key, value in sorted(trends.items())]

    def get_category_wise_expenditure(self, subscriptions):
        """
        Aggregates expenditure per category for pie chart.
        """
        category_data = defaultdict(float)

        for sub in subscriptions:
            category_data[sub.subscription_category] += sub.cost

        # Convert to list
        return [{"category": key, "expenditure": value} for key, value in category_data.items()]

from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import csv
import pandas as pd
from reportlab.pdfgen import canvas
from datetime import datetime
from collections import defaultdict
from decimal import Decimal
from .models import Subscription
from .serializers import SubscriptionSerializer

class GenerateSubscriptionReportView(APIView):
    """
    API View for generating subscription reports based on filters.
    Supports exporting to PDF, CSV, and Excel.
    """
    
    def get(self, request):
        category = request.GET.get("category")
        provider = request.GET.get("provider")
        status_filter = request.GET.get("status")  # active/expired
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        export_format = request.GET.get("export")  # pdf/csv/excel
        
        # Filtering subscriptions
        subscriptions = Subscription.objects.all()
        if category:
            subscriptions = subscriptions.filter(subscription_category=category)
        if provider:
            subscriptions = subscriptions.filter(provider=provider)
        if status_filter == "active":
            subscriptions = subscriptions.filter(end_date__gte=datetime.today().date())
        elif status_filter == "expired":
            subscriptions = subscriptions.filter(end_date__lt=datetime.today().date())
        if start_date and end_date:
            subscriptions = subscriptions.filter(start_date__gte=start_date, end_date__lte=end_date)
        
        if not subscriptions.exists():
            return Response({"message": "No subscriptions found for the selected filters."}, status=status.HTTP_404_NOT_FOUND)
        
        # Export Handling
        if export_format == "csv":
            return self.export_csv(subscriptions)
        elif export_format == "pdf":
            return self.export_pdf(subscriptions)
        elif export_format == "excel":
            return self.export_excel(subscriptions)
        
        # Default JSON Response
        response_data = {
            "subscriptions": SubscriptionSerializer(subscriptions, many=True).data
        }
        return Response(response_data, status=status.HTTP_200_OK)

    def export_csv(self, subscriptions):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="subscription_report.csv"'
        writer = csv.writer(response)
        
        # Write headers
        writer.writerow(["Subscription Name", "Category", "Provider", "Cost", "Start Date", "End Date"])
        
        # Write subscription data
        for sub in subscriptions:
            writer.writerow([
                sub.software_name or sub.server_name or sub.domain_name or sub.utility_name,
                sub.subscription_category, sub.provider, sub.cost, sub.start_date, sub.end_date
            ])
        
        return response
    
    def export_pdf(self, subscriptions):
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="subscription_report.pdf"'
        pdf = canvas.Canvas(response)
        pdf.drawString(100, 800, "Subscription Report")
        
        y = 780
        pdf.drawString(50, y, "Subscription Name | Category | Provider | Cost | Start Date | End Date")
        y -= 20
        
        for sub in subscriptions:
            pdf.drawString(50, y, f"{sub.software_name or sub.server_name or sub.domain_name or sub.utility_name} | {sub.subscription_category} | {sub.provider} | {sub.cost} | {sub.start_date} | {sub.end_date}")
            y -= 20
        
        pdf.showPage()
        pdf.save()
        return response
    
    def export_excel(self, subscriptions):
        response = HttpResponse(content_type="application/vnd.ms-excel")
        response["Content-Disposition"] = 'attachment; filename="subscription_report.xlsx"'
        
        data = [{
            "Subscription Name": sub.software_name or sub.server_name or sub.domain_name or sub.utility_name,
            "Category": sub.subscription_category,
            "Provider": sub.provider,
            "Cost": float(sub.cost),
            "Start Date": sub.start_date,
            "End Date": sub.end_date,
        } for sub in subscriptions]
        
        df = pd.DataFrame(data)
        df.to_excel(response, index=False)
        return response



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
    
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Q, ExpressionWrapper, F, DateField, IntegerField
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Hardware

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
        serializer = HardwareSerializer(data=request.data)
        # serializer = HardwareSerializer(data=request.data, context={'request': request}) 
        
        if serializer.is_valid():
            # serializer.save()
            serializer.save(user=request.user)
            return Response({
                "message": "Hardware successfully added.",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import F

class ListHardwareView(generics.ListAPIView):
    queryset = Hardware.objects.all()
    serializer_class = HardwareSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Allow filtering by Type, Manufacturer, Purchase Date, Assigned Department, Status
    filterset_fields = ['hardware_type', 'manufacturer', 'purchase__purchase_date', 'assigned_department', 'status']
    
    # Allow searching by manufacturer name or assigned department
    search_fields = ['manufacturer', 'assigned_department']

    # Allow sorting by purchase date or status
    ordering_fields = ['purchase__purchase_date', 'status']

    def get_queryset(self):
        queryset = Hardware.objects.all()
        ordering = self.request.query_params.get('ordering', 'purchase__purchase_date')

        if ordering == "purchase__purchase_date":
            return queryset.order_by(F('purchase__purchase_date').asc(nulls_last=True))
        elif ordering == "-purchase__purchase_date":
            return queryset.order_by(F('purchase__purchase_date').desc(nulls_last=True))
        else:
            return queryset.order_by(ordering)
        
class RetrieveUpdateHardwareView(generics.RetrieveUpdateAPIView):
    queryset = Hardware.objects.all()
    serializer_class = HardwareSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        # Partial update (PATCH) or full update (PUT)
        partial = kwargs.get('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)

        if serializer.is_valid():
            self.perform_update(serializer)
            return Response({"message": "Hardware updated successfully", "hardware": serializer.data}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from django.db.models import Sum, Count
from django.utils.timezone import now
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Purchase, HardwareService, Warranty, Hardware


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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework_simplejwt.tokens import RefreshToken

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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Reminder
from .serializers import ReminderSerializer

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


from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Resource
from .serializers import ResourceNameSerializer

class ResourceNameListView(generics.ListAPIView):
    serializer_class = ResourceNameSerializer
    permission_classes = [IsAuthenticated]  # Optional: restrict access to authenticated users

    def get_queryset(self):
        resource_type = self.request.query_params.get('type')
        print("resource_type:",resource_type)
        if resource_type:
            return Resource.objects.filter(resource_type=resource_type)
        return Resource.objects.none()  # Return empty if no resource_type is provided

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({"message": "No resources found for the given type."}, status=404)
        return super().list(request, *args, **kwargs)

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Resource
from .serializers import ResourceSerializer

class ResourceCreateView(generics.CreateAPIView):
    serializer_class = ResourceSerializer
    permission_classes = [IsAuthenticated]  # Restrict access to authenticated users

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Resource created successfully!", "resource": serializer.data},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from datetime import timedelta
from django.utils.timezone import now
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from SubSync.models import Subscription, Hardware, Customer
from django.utils.timezone import now
from django.db.models import Sum
from django.db.models import F, ExpressionWrapper, DurationField

class DashboardOverviewAll(APIView):
    permission_classes = [IsAuthenticated]  # Secure the endpoint

    def get(self, request):
        today = now().date()
        next_week = today + timedelta(days=7)
        next_month = today.replace(day=1) + timedelta(days=32)  # Approx next month start

        # Active Counts
        # total_active_subscriptions = Subscription.objects.filter(status="Active").count()
        total_active_customers = Customer.objects.filter(status="Active").count()
        total_active_hardware = Hardware.objects.filter(status="Active",is_deleted=False).count()
        total_hardware=Hardware.objects.filter(is_deleted=False).count()

        active_count = Subscription.objects.filter(end_date__gte=now()).count()
        expired_count = Subscription.objects.filter(end_date__lt=now()).count()

        # Monthly Cost Analysis
        # Get first and last day of the current month
        today = now().date()
        first_day = today.replace(day=1)
        # 1️⃣ Total subscription cost for the current month
        total_subscription_cost = Subscription.objects.filter(
            status="Active",
            start_date__gte=first_day,  # Ensure the subscription started in the current month
        ).aggregate(total_cost=Sum("cost"))["total_cost"] or 0
        # total_subscription_cost = Subscription.objects.filter(status="Active").aggregate(total_cost=Sum("cost"))["total_cost"] or 0

        # 2️⃣ Total hardware cost (purchase + maintenance) for the current month
        purchase_cost = Hardware.objects.filter(
            is_deleted=False,
            purchase__purchase_date__gte=first_day  # Ensure the purchase was in the current month
        ).aggregate(total_cost=Sum("purchase__purchase_cost"))["total_cost"] or 0

        # 3️⃣ Add maintenance cost if it's stored separately
        next_service_expr = ExpressionWrapper(
            F("service__last_service_date") + F("service__service_period") * timedelta(days=1),
            output_field=DurationField()
        )

        maintenance_cost = Hardware.objects.annotate(next_service_date=next_service_expr).filter(
            next_service_date__gte=first_day  # Correct filter placement
        ).aggregate(total_cost=Sum("service__service_cost"))["total_cost"] or 0
        
        print("purchase cost",purchase_cost,"maintanace cost", maintenance_cost)
        # 4️⃣ Final hardware cost including maintenance
        total_hardware_cost = purchase_cost + maintenance_cost
        # total_hardware_cost = Hardware.objects.filter(is_deleted=False).aggregate(total_cost=Sum("purchase__purchase_cost"))["total_cost"] or 0

        # Subscription Warnings (Renewal in next 7 days)
        renewal_subscriptions = Subscription.objects.filter(next_payment_date__range=[today, next_week]).count()

        # Hardware Warnings
        warranty_expiring = Hardware.objects.filter(is_deleted=False, warranty__warranty_expiry_date__lte=now() + timedelta(days=30)).count()
        maintenance_due = Hardware.objects.filter(status="maintenance_due", is_deleted=False).count()
        # out_of_warranty = Hardware.objects.filter(is_deleted=False, warranty__warranty_expiry_date__lte=now()).count()

        # Total Warnings Count
        total_warnings = renewal_subscriptions + warranty_expiring + maintenance_due 
        return Response({
            "total_active_subscriptions": active_count,
            "total_active_customers": total_active_customers,
            "total_active_hardware": total_active_hardware,
            "total_hardware":total_hardware,
            "expired_count": expired_count,

            "subscription_cost": total_subscription_cost,
            "hardware_cost": total_hardware_cost,
            "renewal_subscriptions": renewal_subscriptions,
            "warranty_expiring": warranty_expiring,
            "maintenance_due": maintenance_due,
            "total_warnings": total_warnings

            # "monthly_cost_analysis": {
            #     "subscription_cost": total_subscription_cost,
            #     "hardware_cost": total_hardware_cost
            # },

            # "warnings": {
            #     "renewal_subscriptions": renewal_subscriptions,
            #     "warranty_expiring": warranty_expiring,
            #     "maintenance_due": maintenance_due,
            #     # "out_of_warranty": out_of_warranty,
            #     "total_warnings": total_warnings
            # }
        })


from rest_framework import generics, permissions
from rest_framework.response import Response
from SubSync.models import Notification
from SubSync.serializers import NotificationSerializer

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
