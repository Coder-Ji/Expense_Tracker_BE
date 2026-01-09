from django.urls import path
from .views import get_transcations, upload_transcations, create_transcation,delete_transcation,total_income_outgoes,user_login,get_filters

urlpatterns =[
    path('get_transcations/',get_transcations),
    path('upload_transaction/',upload_transcations),
    path('create/',create_transcation),
    path('delete/',delete_transcation),
    path('total_expense_income/',total_income_outgoes),
    path('login/',user_login),
    path('filters-available/',get_filters )
]
