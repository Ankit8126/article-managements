from django.urls import path,include
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'users'  

urlpatterns=[
    path('registration/',views.register, name='register'),
    path('login/',views.login,name='login'),
    path('forget_password/', views.forgetPass, name="Forget_password"),
    path('varify_otp/', views.varifyOTP, name='Varify_OTP'),
    path('reset_password/', views.resetPass, name="Reset_password")
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)