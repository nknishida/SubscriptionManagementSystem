from django.urls import path
from .views import ActiveSubscriptionsView, AddHardwareAPIView, DashboardOverview, DashboardOverviewAll, ExpiredSubscriptionsView, HardwareSummaryView, ListHardwareView, LoginAPIView, ForgotPasswordAPIView, LogoutView, MarkNotificationAsReadView, NotificationListView, ProviderListView, ReminderAPIView, ResetPasswordAPIView, CreateUserAPIView, ResourceCreateView, ResourceNameListView, RetrieveUpdateHardwareView, SubscriptionCategoryDistributionView, SubscriptionChoicesView, SubscriptionCountView, SubscriptionCreateView, ProviderCreateView,ChangePasswordView, SubscriptionListView, SubscriptionDetailView, SubscriptionMonthlyAnalysisView, UpcomingHardwareAPIView, UserProfileView, WarningSubscriptionsView, hardware_report, spending_report
from .views import SubscriptionDetailUpdateView, ExpenditureAnalysisView
from rest_framework_simplejwt import views as jwt_views

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('create-user/', CreateUserAPIView.as_view(), name='create-user'),

    path('add-subscription/', SubscriptionCreateView.as_view(), name='add-subscription'),
    path('subscriptions/', SubscriptionListView.as_view(), name='subscriptions-list'),  # GET for listing & filtering
    path('subscriptions/details/<int:id>/', SubscriptionDetailView.as_view(), name='subscription-detail'),
    path("subscriptions/update/<int:pk>/", SubscriptionDetailUpdateView.as_view(), name="subscription-detail-update"),
    path('providers/', ProviderCreateView.as_view(), name='provider-create'),

    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    path("subscriptions/expenditure/", ExpenditureAnalysisView.as_view(), name="expenditure-analysis"),

    path('hardware/add/', AddHardwareAPIView.as_view(), name='add-hardware'),
    path('hardware/', ListHardwareView.as_view(), name='list-hardware'),

    path('dashboard_overview/', DashboardOverview.as_view(), name='dashboard_overview'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),

    path('subscriptions_active/', ActiveSubscriptionsView.as_view(), name='active-subscriptions'),
    path('subscriptions_expired/', ExpiredSubscriptionsView.as_view(), name='expired-subscriptions'),
    path('subscriptions_warnings/', WarningSubscriptionsView.as_view(), name='warning-subscriptions'),
    path('subscription_count/', SubscriptionCountView.as_view(), name='subscription-count'),
    path('subscriptions_category_distribution/', SubscriptionCategoryDistributionView.as_view(), name='category-distribution'),
    path('subscriptions_monthly-analysis/', SubscriptionMonthlyAnalysisView.as_view(), name='monthly-analysis'),

    path('hardware_summary/', HardwareSummaryView.as_view(), name='hardware-summary'),
    path("upcoming_hardware/", UpcomingHardwareAPIView.as_view(), name="upcoming-hardware"),

    path('view_providers/', ProviderListView.as_view(), name='provider-list'),

    path('hardware/<int:pk>/', RetrieveUpdateHardwareView.as_view(), name='retrieve-update-hardware'),
    path('spending-reports/', spending_report, name='spending-reports'),

    path("subscription_choices/", SubscriptionChoicesView.as_view(), name="subscription-choices"),

    path('hardware-report/', hardware_report, name='hardware-report'),
    
    path('logout/', LogoutView.as_view(), name='logout'),

    path('reminders/', ReminderAPIView.as_view(), name='reminder-list'),
    path('reminders/<int:pk>/', ReminderAPIView.as_view(), name='reminder-detail'),

    path('resources/names/', ResourceNameListView.as_view(), name='resource-names'),
    path('resources/add/', ResourceCreateView.as_view(), name='resource-add'),
    
    # path('token/', jwt_views.TokenObtainPairView.as_view(), name = 'token'),
    path('token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
    path('dashboard/', DashboardOverviewAll.as_view(), name='all'),

    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/<int:pk>/", MarkNotificationAsReadView.as_view(), name="mark-notification-read"),

]
