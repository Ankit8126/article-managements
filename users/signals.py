from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CustomUser, Profile

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)  # Ensures no duplicate profile creation

# @receiver(post_save, sender=CustomUser)
# def save_user_profile(sender, instance, **kwargs):
#     # Ensure the profile is saved when the user is saved
#     if hasattr(instance, 'profile'):
#         instance.profile.save()
