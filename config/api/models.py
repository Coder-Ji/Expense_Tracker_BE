from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class VersionHistory(models.Model):
     file_name = models.CharField()
     uploaded_at = models.DateTimeField(auto_now_add=True)
     user=models.ForeignKey(User,on_delete=models.CASCADE)
     def __str__(self):
          return f"{self.file_name}"

class Category(models.Model):
      name = models.CharField(max_length=50,unique=True)
      color = models.CharField(max_length=7) 
      uploaded_version = models.ForeignKey(VersionHistory,on_delete=models.CASCADE,related_name="category_version")

      def __str__(self):
        return f"{self.name}"     

class Transcations(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE)
    ref_no = models.CharField(max_length=50,null=True)
    date = models.DateField(null=True)
    narration = models.TextField(null=True)
    debit_amount = models.FloatField(default=0.0)  
    credit_amount = models.FloatField(default=0.0)  
    closing_balance = models.FloatField(default=0.0)
    value_date = models.CharField()
    category = models.ForeignKey(Category,on_delete=models.SET_NULL,null=True,related_name="transactions")
    type = models.CharField(max_length=50)
    amount = models.FloatField(default=0.0)
    currency = models.CharField(max_length=5)
    merchant=models.CharField(max_length=50)
    cheque_info = models.CharField(null=True)
    uploaded_version = models.ForeignKey(VersionHistory,on_delete=models.CASCADE,related_name="version")

    def __str__(self):
        return f"{self.narration} - {self.ref_no}"
    
