from django.urls import path
from .views import LoginAPIView, ForgotPasswordAPIView, ResetPasswordAPIView, CreateUserAPIView, SubscriptionCreateView

urlpatterns = [
    path('login/', LoginAPIView.as_view(), name='login'),
    path('forgot-password/', ForgotPasswordAPIView.as_view(), name='forgot_password'),
    path('reset-password/', ResetPasswordAPIView.as_view(), name='reset_password'),
    path('create-user/', CreateUserAPIView.as_view(), name='create-user'),
    path('add-subscription/', SubscriptionCreateView.as_view(), name='add-subscription'),





]
