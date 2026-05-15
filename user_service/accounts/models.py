from django.db import models
from django.contrib.auth.models import User
import uuid
from datetime import datetime,timedelta
from django.utils import timezone

class ProfileTypeChoice(models.TextChoices):
    SUPER_ADMIN = "Super Admin"
    ORGANIZATION_ADMIN = "Organization_Admin"

# Create your models here.
class UserProfile(models.Model):
    id = models.AutoField(primary_key=True)
    profile_unique_id = models.UUIDField(editable=False, default=uuid.uuid4, unique=True, db_index=True)
    profile_phone = models.CharField(default='', max_length=9000, blank=True, null=True)
    profile_user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE, db_index=True)
    profile_organization = models.CharField(default='', max_length=9000)
    profile_type = models.CharField(default='Organization_Admin', choices = ProfileTypeChoice.choices, max_length=9000)
    profile_is_active = models.BooleanField(default=True, db_index=True)
    profile_created_date = models.DateField(auto_now_add=True)
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['-id']
        verbose_name_plural = "USER PROFILES"

    def __str__(self):
        return f"{self.profile_organization} : {self.profile_user.first_name} {self.profile_user.last_name}"

class SavePasswordRequestUsers(models.Model):
    primary_key = models.AutoField(primary_key=True)
    save_pswd_user = models.ForeignKey(User, related_name='password_profile', on_delete=models.CASCADE)
    save_pswd_token = models.CharField(max_length=300, editable=False, default=None)
    save_pswd_is_used = models.BooleanField(default=False)
    save_pswd_is_active = models.BooleanField(default=True)
    # save_pswd_expiration_time = models.DateTimeField()
    
    class Meta:
        db_table = 'save_password_request'
        ordering = ['-primary_key']
        verbose_name_plural = "SAVE PASSWORD REQUESTS"

    def __str__(self):
        return "{} - {}".format(self.save_pswd_user, self.save_pswd_token)


class ForgotPasswordRequestUser(models.Model):
    primary_key = models.AutoField(primary_key=True)
    request_user = models.ForeignKey(User, related_name='request_profile', on_delete=models.CASCADE)
    request_token = models.CharField(max_length=300, editable=False, default=None)
    request_is_used = models.BooleanField(default=False)
    request_is_active = models.BooleanField(default=True)
    request_created_date = models.DateTimeField(auto_now_add=True)
    request_expiration_time = models.DateTimeField()
    class Meta:
        db_table = 'users_forgot_password_request'
        ordering = ['-primary_key']
        verbose_name_plural = "FORGOT PASSWORD REQUESTS"

    def __str__(self):
        return f"{self.request_user} - {self.request_token}"

    def has_expired(self):
        # Calculate the time difference between now and request_created_date
        current_time = datetime.now()
        time_difference = current_time - self.request_created_date

        # Check if the time difference is greater than 24 hours (86400 seconds)
        if time_difference.total_seconds() > 86400:
            return True
        
        return False


class ActivateAccountTokenUser(models.Model):
    primary_key = models.AutoField(primary_key=True)
    token_user = models.ForeignKey(User, related_name='token_user', on_delete=models.CASCADE)
    token_token = models.CharField(max_length=300, editable=False, default=None)
    token_is_used = models.BooleanField(default=False)
    token_is_active = models.BooleanField(default=True)
    token_created_date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users_activate_account_token'
        ordering = ['-primary_key']
        verbose_name_plural = "ACTIVATE ACCOUNT TOKEN"

    def __str__(self):
        return f"{self.token_user} - {self.token_token}"

    def has_expired(self):
        # Get the current time in UTC
        current_time = timezone.now()
        
        # Calculate the time difference between now and token_created_date
        time_difference = current_time - self.token_created_date

        # Define a timedelta of 24 hours
        expiration_period = timedelta(hours=24)

        # Check if the time difference is greater than the expiration period
        if time_difference > expiration_period:
            return True
        return False