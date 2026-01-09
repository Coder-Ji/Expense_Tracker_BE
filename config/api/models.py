from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Transcations(models.Model):
    ref_no = models.CharField(max_length=50,null=True)
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    date = models.DateField(null=True)
    narration = models.TextField(null=True)
    debit_amount = models.FloatField(default=0.0)  
    credit_amount = models.FloatField(default=0.0)  
    closing_balance = models.FloatField(default=0.0)
    value_date = models.CharField()
    category = models.CharField(max_length=50)
    type = models.CharField(max_length=50)
    amount = models.FloatField(default=0.0)
    currency = models.CharField(max_length=5)
    merchant=models.CharField(max_length=50)
    color=models.CharField(max_length=7)
    cheque_info = models.CharField(null=True)

    def __str__(self):
        return f"{self.narration} - {self.ref_no}"