from celery import shared_task
from .models import Loan
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import date

@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Loan.DoesNotExist:
        pass

@shared_task
def check_overdue_loans():
    today = timezone.now().date()
    overdue_loans = Loan.objects.filter(is_returned=False, due_date__lt=today).select_related('member__user', 'book')

    notification_sent = 0
    
    for loan in overdue_loans:
        try:
            member_email = loan.member.user.email
            if member_email:
                days_overdue = (today - loan.due_date).days
                send_mail(
                    subject='Overdue Book Return Reminder',
                    message=f'Hello {loan.member.user.username}',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[member_email],
                    fail_silently=False 
                )
                notification_sent += 1
        except Exception as e:
            print(f"Error {e}")

    return f"Sent {notification_sent} overdue loan notification"