from rest_framework import status, permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from api.permissions import IsEditorOrAdmin,IsAdminUser
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from api.serializers.user_serializers import (
    RegistrationSerializer, LoginSerializer, 
    UserSerializer, UserUpdateSerializer, 
    ChangePasswordSerializer, PasswordResetSerializer
)
from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # Number of users per page
    page_size_query_param = 'page_size'  # Allow clients to set page size
    max_page_size = 100  # Maximum page size limit

User = get_user_model()

# User Registration View
class UserRegistrationView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]  # Allow anyone to register

    def create(self, request, *args, **kwargs):
        # Get the serializer and validate the input data
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            # If validation passes, save the user and get the user data
            user = serializer.save()
            user_data = serializer.data
            return Response({
                'status': 'Success',
                'message': 'Registration successful.',
                'user': user_data
            }, status=status.HTTP_201_CREATED)
        except serializers.ValidationError as e:
            # If validation fails, return the error dictionary
            print(e)
            return Response({
                'status': 'Failure',
                'errors': e.detail
            }, status=status.HTTP_400_BAD_REQUEST)


# User Login View
class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]  # Allow anyone to login

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'refresh': str(refresh),
                'token': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
            # token, created = Token.objects.get_or_create(user=user)
            # return Response({
            #     'token': str(token),
            #     'user': UserSerializer(user).data  # Optionally, include user details
            # })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(generics.ListAPIView):
    """
    View to list users with filtering by username, role, and joining date.
    Only accessible by Admins.
    """
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    # authentication_classes = [TokenAuthentication]
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        """
        Filter users dynamically based on query parameters:
        - Filter by username (partial match).
        - Filter by role (exact match).
        - Filter by exact joining date.
        """
        queryset = User.objects.all().order_by('-id')  # Default queryset

        # Filter by username (case-insensitive partial match)
        username = self.request.query_params.get('username', None)
        if username:
            queryset = queryset.filter(username__icontains=username)

        # Filter by role (case-insensitive exact match)
        role = self.request.query_params.get('role', None)
        if role:
            queryset = queryset.filter(role__iexact=role)

        # Filter by exact joining date
        date_joined = self.request.query_params.get('date_joined', None)
        if date_joined:
            try:
                # Convert to datetime object
                date_obj = datetime.strptime(date_joined, '%Y-%m-%d')
                # Make it timezone-aware
                date_obj = timezone.make_aware(date_obj, timezone.get_current_timezone())
                queryset = queryset.filter(date_joined__date=date_obj.date())  # Use only the date part for filtering
            except ValueError:
                # Handle invalid date format
                pass

        return queryset


# User Detail View (Single User)
class UserDetailView(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]  # Any logged-in user can see their details
    # authentication_classes = [TokenAuthentication]

# User Update View (Update User Data)
class UserUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]  # Only authenticated users can update their data

    def get_object(self):
        return self.request.user  # Allow user to update only their own data

class UsersUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if self.request.user.is_staff:
            return User.objects.get(id=self.kwargs['id'])
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": "Success", "message": "Profile updated successfully!"}, status=status.HTTP_200_OK)
        return Response({"status": "Error", "message": "Failed to update profile.", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

# Change Password View
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']
            
            # Check if the old password is correct
            if not user.check_password(old_password):
                return Response({'error': 'Old password is incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if the new password matches the old password
            if old_password == new_password:
                return Response({'error': 'New password cannot be the same as the old password.'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Update password
            user.set_password(new_password)
            user.save()
            return Response({'status': 'Success'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# Password Reset Request View
class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]  # Anyone can request password reset

    def post(self, request, *args, **kwargs):
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request)
            return Response({'message': 'Password reset email sent.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Delete User View
class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAdminUser]  # Only admin can delete users

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        return Response({
            'message': 'User deleted successfully.'
        }, status=status.HTTP_204_NO_CONTENT)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # Get the token from the request header
        refresh_token = request.data.get('refresh')
        if not refresh_token:
                return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        token = RefreshToken(refresh_token)
        token.blacklist()
        # Delete the token to effectively log the user out
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
    


from django.core.mail import send_mail
import random
from api.serializers.user_serializers import OTPPasswordResetSerializer, PasswordResetWithOTPSerializer,OTPVerificationSerializer
class RequestOTPView(APIView):
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = OTPPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({"detail": "User not found."}, status=status.HTTP_400_BAD_REQUEST)

            # Generate a random OTP (6 digits)
            otp = str(random.randint(100000, 999999))

            # Save OTP temporarily (can be in the session, or you can use Django cache, etc.)
            # For this example, we'll assume it's stored in the context
            request.session['otp'] = otp
            request.session['otp_email'] = email  # Storing email to match OTP

            # Send OTP via email
            send_mail(
                subject="Reset Your Password - OTP Inside",  # A clear and user-friendly subject
                message=(
                    f"Hello,\n\n"
                    f"We received a request to reset your password. Please use the following One-Time Password (OTP) to proceed:\n\n"
                    f"🔒 Your OTP: {otp}\n\n"
                    f"If you did not request a password reset, please ignore this email or contact our support team.\n\n"
                    f"Best regards,\n"
                    f"ArticleHub Team"
                ),
                from_email="support@articlehub.com",  # Your email address or support email
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({"detail": "OTP sent to your email."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class OTPVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = OTPVerificationSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Redirect user to the password reset page after OTP verification
            # You can set a flag in session or pass data as needed for the next page
            return Response({'message': 'OTP verified successfully.'}, 
                             status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetWithOTPView(APIView):
    permission_classes = [permissions.AllowAny]  # Or any other permission as needed
    
    def post(self, request, *args, **kwargs):
        serializer = PasswordResetWithOTPSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # Process the password reset after OTP validation
            user = serializer.save()
            email = User.objects.get(username=user).email

            # Invalidate OTP by removing it from the session
            if 'otp' in request.session:
                del request.session['otp']
            if 'otp_email' in request.session:
                del request.session['otp_email']

            # Notify user about password change
            send_mail(
                subject="Your Password Has Been Successfully Updated",  # Clear and reassuring subject
                message=(
                    f"Hello,\n\n"
                    f"We wanted to let you know that your password has been successfully updated. "
                    f"If you made this change, no further action is required.\n\n"
                    f"If you did not request this change, please contact our support team immediately to secure your account.\n\n"
                    f"Best regards,\n"
                    f"ArticleHub Team"
                ),
                from_email="support@articlehub.com",  # Your email address or support email
                recipient_list=[email],
                fail_silently=False,
            )

            return Response({'message': 'Password reset successful.'}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    


from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

class ValidateTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
        })
