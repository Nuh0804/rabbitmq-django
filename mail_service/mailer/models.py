from django.db import models
import uuid

# Create your models here.

class EmailStatus(models.Model):
    id = models.AutoField(primary_key=True)
    unique_id = models.UUIDField(editable=False, default=uuid.uuid4, unique=True, db_index=True)
    email_recipient = models.CharField(max_length = 100)
    email_type = models.CharField(max_length = 50)
    email_user = models.JSONField()
    is_sent = models.BooleanField(default = False)
    retries = models.IntegerField()
    email_created_date = models.DateField(auto_now_add=True)

    class Meta:
        db_table = 'email_status'
        ordering = ['-id']
        verbose_name_plural = "EMAIL STATUSES"

    def __str__(self):
        return f"{self.email_recipient} : {self.email_type} {self.is_sent}"