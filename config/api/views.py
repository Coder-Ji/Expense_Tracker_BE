from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework import status
from django.db.models import Q
import pandas as pd
import numpy as np
from django.db import transaction
from django.contrib.auth import authenticate
from .models import Transcations,Category,VersionHistory 
from .serializers import TransactionSerializer,VersionHistorySearlizer
from django.db.models import Sum
from datetime import datetime
import pdfplumber
import random
import os   

@api_view(["POST"])
@permission_classes([AllowAny])
def user_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username,password=password)

    if not user:
        return Response({'error' : 'User not found'},status=status.HTTP_404_NOT_FOUND)
    
    try:
        token, created = Token.objects.get_or_create(user=user)
    except Token.DoesNotExist:
        return Response({"error" : 'Token issue'},status=status.HTTP_404_NOT_FOUND)

    # print(token,created)

    return Response({"token" : token.key,"user" : user.username})


@api_view(['GET'])
def get_transcations(request):
    try:
        user = request.user
        user_selected_filter = request.GET.get('filter')
        searched_text = request.GET.get('search') or ""
        if user_selected_filter != "All":
            filter_month = datetime.strptime(user_selected_filter,'%b-%y')
            data = Transcations.objects.filter(
                user=user,
                date__year=filter_month.year,
                date__month=filter_month.month
            )
        else :
            data = Transcations.objects.filter(
                user=user
            )
        filtered_transactions = data.filter(
            Q(category__name__icontains=searched_text)
            | Q(merchant__icontains=searched_text)
            | Q(type__icontains=searched_text)
            | Q(ref_no__icontains=searched_text)
        )
        # print(filtered_transactions.select_related("category"))
        serailizedObject = TransactionSerializer(filtered_transactions, many=True)
        return Response({"data": serailizedObject.data},status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)},status=status.HTTP_417_EXPECTATION_FAILED)
    
def color_gen():
    letters = '0123456789ABCDEF'
    color = '#'
    existing_colors=[]

    for c in Category.objects.all():
        print(c)
        existing_colors.append(c.color)

    for _ in range(6):
        color += random.choice(letters) 

    if existing_colors.__contains__(color):
        return color_gen()    
    return color   


color_for_categories = {}    

def getColors(category):
    # print(list(Category.objects.all()))

    if category in color_for_categories:
        return color_for_categories[category]
    else:
        color = color_gen()
        color_for_categories[category] = color
        return color_for_categories[category]


def generic_formatter(df,user,file):
    # print(df)
    # Convert date column to proper datetime.date
    df["date"] = pd.to_datetime(df["date"],dayfirst=True , errors="coerce").dt.date
    df = df.dropna(subset=["date"])
    # Clean numeric columns
    for col in ["debit_amount", "credit_amount", "closing_balance"]:
        df[col] = df[col].astype(str).str.replace(",", "", regex=False)
        df[col] = pd.to_numeric(df[col],errors="coerce").fillna(0.0)
    df["type"] = np.where(df["debit_amount"] == 0, "Income", "Expense")
    df["amount"] = np.where(
        df["debit_amount"] == 0, df["credit_amount"], df["debit_amount"]
    )
    df["color"] = df["category"].apply(getColors)
    df["currency"] = "inr"
    df['user'] = user

    category_names = df['category'].dropna().astype('str').str.strip().str.upper().replace("",np.nan).dropna().unique()

    existing_categories = Category.objects.filter(name__in=category_names)

    category_map = {c.name : c for c in existing_categories}

    verision =VersionHistory.objects.create(file_name=file.name,user=user)


    new_categories = [
        Category(name=name,color=getColors(name),uploaded_version=verision)
        for name in category_names
        if name not in category_map
    ]

    Category.objects.bulk_create(new_categories)

    all_categories = Category.objects.filter(name__in=category_names)

    category_map = {c.name : c for c in all_categories}

    transactions = []

    # df['category'] = category_map.get(df['category'])
    # Category.objects

    for row in df.to_dict(orient="records"):
        transactions.append(
            Transcations(
                user = user,
                ref_no = row["ref_no"],
                date=row["date"],
                value_date=row["value_date"],
                narration=row["narration"],
                debit_amount=row["debit_amount"],
                credit_amount=row["credit_amount"],
                closing_balance=row["closing_balance"],
                amount=row["amount"],
                merchant=row["merchant"],
                category=category_map.get(row['category']),
                uploaded_version=verision,
                currency="inr",
                type=row["type"] 
            )
        )

    with transaction.atomic():
        Transcations.objects.bulk_create(transactions,ignore_conflicts=False)

    print(transactions)
    
    return df


@api_view(['POST'])
def upload_transcations(request):
    if 'file' not in request.FILES:
        return Response({"error": "No File Received"}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    file = request.FILES['file']
    file_extension = os.path.splitext(file.name)[1]
    # print(file_extension)
    if file_extension == '.pdf':
        try:
            import_pdf(file,user=user)
            return Response({"data" : "file"})
        except Exception as e:
            return Response({"error" : str(e)})
    else:
        try:
            # Read Excel, skip first 20 rows and last 16 rows
            df = pd.read_excel(file, skiprows=20, skipfooter=16, header=0)


            # print(dr.id,'djididhiu')

            # Rename columns to match your model
            df = df.rename(columns={
                "Chq./Ref.No.": "ref_no",
                "Date": "date",
                "Narration": "narration",
                "Deposit Amt.": "credit_amount",
                "Withdrawal Amt.": "debit_amount",
                "Closing Balance": "closing_balance",
                "Value Dt": "value_date"
            })

            # custom logic columns
            # HDFC-xlsx
            cleaned = df['narration'].str.replace(r'\d+', '', regex=True)
            df['category'] = np.where(df['narration'].str.contains("EMI|POS|INTEREST",case=False,na=False), cleaned.str.split(' ',n=1).str[0], cleaned.str.split('-',n=1).str[0])
            df['merchant'] = np.where(df['narration'].str.contains("EMI|INTEREST",case=False,na=False), cleaned.str.split(' ',n=2).str[1], np.where(df['narration'].str.contains("POS",case=False,na=False), cleaned.str.split(' ').str[2:].str.join(" "), cleaned.str.split('-',n=2).str[1]))
            # print(df,'skisj')
            df = generic_formatter(df,user=user,file=file)
            

            return Response({"message": "Transactions uploaded successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            print("Error uploading transactions:", e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def create_transcation(request):
    serializer = TransactionSerializer(data = request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message' : 'Successfully Created'},status=status.HTTP_200_OK)
    else:
        return Response({'error' : 'transcation is not valid'},status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
def delete_transcation(request):
    try:
        deleting_transaction = Transcations.objects.get(id=request.data["id"])
        deleting_transaction.delete()
        return Response({"message" : 'sucessfully deleted'})
    except Exception as e:
        return Response({'error' : e })

@api_view(['GET'])
def total_income_outgoes(request):
    try:
        user = request.user
        searched_text=request.GET.get("search") or ""
        filter = request.GET.get("filter")
        if filter != "All":
            format_filter = datetime.strptime(filter, "%b-%y")
            trans = Transcations.objects.filter(
                user=user,
                date__year=format_filter.year,
                date__month=format_filter.month,
            ).filter(
                Q(category__name__icontains=searched_text)
                | Q(merchant__icontains=searched_text)
                | Q(type__icontains=searched_text)
            )
            total = trans.aggregate(
                total_income=Sum("credit_amount"), total_expense=Sum("debit_amount")
            )
            closing_balance = (
                trans.order_by("-date")
                .values_list("closing_balance", flat=True)
                .first()
            )
        else:
            trans = Transcations.objects.filter(user=user).filter(
                Q(category__name__icontains=searched_text) 
                | Q(merchant__icontains=searched_text)
                | Q(type__icontains=searched_text)
            )
            total = (
                trans
                .aggregate(
                    total_income=Sum("credit_amount"), total_expense=Sum("debit_amount")
                )
            )
            closing_balance = (
                trans
                .order_by("-date")
                .values_list("closing_balance", flat=True)
                .first()
            )
        return Response({"data": total | {"closing_balance": closing_balance}})
    except Exception as e:
        return Response({"error":str(e)})

def import_pdf(file,user):
        data = []
        if "CUB":
            with pdfplumber.open(file) as pdf:
                for _,page in enumerate(pdf.pages):
                    table = page.extract_table()
                    if table:
                        df = pd.DataFrame(table[1::],columns=table[0])
                        data.append(df)
            finaldf = pd.concat(data,ignore_index=True)
            # Rename columns to match your model
            finaldf = finaldf.rename(columns={
                "DATE": "date",
                "DESCRIPTION": "narration",
                "CREDIT": "credit_amount",
                "DEBIT": "debit_amount",
                "BALANCE": "closing_balance",
                "CHEQUE NO":"cheque_info"
            })
            cleaned = finaldf['narration'].str.replace('\n','-')
            finaldf['ref_no'] = np.where(
                cleaned.str.contains("BY INT|ATM"),
                cleaned.str.split(':' , n=3).str[2],
                cleaned.str.split('/' , n=3).str[2])
            finaldf["category"] = np.where(
                cleaned.str.contains("BY INT|ATM|INTEREST"),
                np.where(cleaned.str.contains("BY INT|INTEREST"), "INT", "ATM"),
                np.where(
                    cleaned.str.contains(
                        "DEP OPEN|DEP CLOS|PAYMENT:TRANSFER|CHARGES|CARD CHARGE|CASH DEPOSIT|TRF"
                    ),
                    cleaned.str.split(" ", n=2).str[2].str.split(":", n=1).str[0],
                    cleaned.str.split(" ", n=2).str[2].str.split("/", n=1).str[0],
                ),
            )
            finaldf["merchant"] = np.where(
                cleaned.str.contains("BY INT|ATM|INTEREST"),
                'N/A',
                np.where(
                    cleaned.str.contains(
                        "DEP OPEN|DEP CLOS|PAYMENT:TRANSFER|CHARGES|CARD CHARGE|CASH DEPOSIT|BY ONL TRF"
                    ),
                    'N/A',
                    cleaned.str.split("/", n=4).str[3],
                ),
            )
            finaldf = generic_formatter(df=finaldf,user=user,file=file)
            # with transaction.atomic():
            #     Transcations.objects.bulk_create(
            #         [Transcations(**row) for row in finaldf.to_dict(orient='records')]
            #     )

@api_view(['GET'])
def get_filters(request):
    try:
        user = request.user
        dates = Transcations.objects.filter(user=user).dates('date','month',order="ASC")
        formatted_months = [m.strftime('%b-%y') for m in dates]
        transaction_start_date = Transcations.objects.filter(user=user).order_by('date').values_list('date',flat=True).first()
        transaction_end_date = Transcations.objects.filter(user=user).order_by('-date').values_list('date',flat=True).first() 

        result = {
            "availble_months": formatted_months,
            "transaction_start_date": transaction_start_date,
            "transaction_end_date": transaction_end_date,
        }
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(["GET"])
def get_uploaded_files(request):
    try:
        user = request.user
        versions =  VersionHistorySearlizer(VersionHistory.objects.filter(user=user),many=True)
        return Response({"data" : versions.data})
    except Exception as e:
        return Response({'error' : e})


@api_view(["DELETE"])
def delete_uploaded_file(request):
    try:
        # print(request.GET.get("id"))
        delete_file = VersionHistory.objects.get(id=request.GET.get("id"))
        delete_file.delete()
        return Response({"Message" : "Successfully Deleted"})
    except Exception as e :
        return Response({'error' : str(e)})