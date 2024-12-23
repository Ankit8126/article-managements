from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.
def register(request):
    return render(request,'registration/signup.html')
def login(request):
    return render(request,'registration/login.html')
def forgetPass(request):
    return render(request,'registration/password_forget.html')
def varifyOTP(request):
    return render(request,'registration/otp_page.html')
def resetPass(request):
    return render(request,'registration/reset_password.html')