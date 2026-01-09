from rest_framework import serializers
from .models import Transcations

class TransactionSerializer(serializers.ModelSerializer):
    class Meta :
        model = Transcations
        fields = '__all__'