from rest_framework import serializers
from .models import Transcations,Category,VersionHistory

class CategorySearalizer(serializers.ModelSerializer):
    class Meta :
        model = Category
        fields = ["id","name","color"]

class VersionHistorySearlizer(serializers.ModelSerializer):
    class Meta:
        model = VersionHistory
        fields = '__all__'

class TransactionSerializer(serializers.ModelSerializer):
    category = CategorySearalizer(read_only=True)
    class Meta :
        model = Transcations
        fields = '__all__'