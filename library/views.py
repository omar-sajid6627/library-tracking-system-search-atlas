from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from .tasks import send_loan_notification
from datetime import timedelta
from django.db import connection

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        return Book.objects.select_related('author').all()
    
    def list(self, request, *args, **kwargs):
        initial_queries = len(connection.queries)
        response = super().list(request, *args, **kwargs)

        final_queries = len(connection.queries)
        query_count = final_queries - initial_queries

        return response


    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=['post'])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()

        if loan.is_returned:
            return Response(
                {'error': 'error'},
                status = status.HTTP_400_BAD_REQUEST
            )
        additional_days = request.data.get('additional_days')

        if additional_days is None:
            return Response(
                {'error': 'error'},
                status = status.HTTP_400_BAD_REQUEST
            )
        try:
            additional_days = int(additional_days)
        except (ValueError, TypeError):
            return Response(
                {'error': 'error'},
                status = status.HTTP_400_BAD_REQUEST
            )
        
        if additional_days <= 0:
            return Response(
                {'error': 'error'},
                status = status.HTTP_400_BAD_REQUEST
            )
        
        old_due_date = loan.due_date
        loan.due_date = loan.due_date + timedelta(days=additional_days)
        loan.save()


        serializer = self.get_serializer(loan)
        return Response(
                {
                    'message': f'Due date extended by {additional_days} days',
                    'old_due_date': old_due_date,
                    'new_due_date': loan.due_date,
                    'loan': serializer.data
                },
                status=status.HTTP_200_OK
            )