from __future__ import annotations

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from apps.tenancy.models import EmailQueue


@shared_task(name="apps.tenancy.tasks.process_email_queue_task")
def process_email_queue_task(batch_size: int = 200) -> dict:
    pending = EmailQueue.objects.filter(status=EmailQueue.STATUS_PENDING).order_by(
        "created_at"
    )[:batch_size]
    sent_count = 0
    failed_count = 0

    for item in pending:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")
        email = EmailMultiAlternatives(
            subject=item.subject,
            body=item.text_body,
            from_email=from_email,
            to=[item.to_email],
        )
        if item.html_body:
            email.attach_alternative(item.html_body, "text/html")

        try:
            email.send(fail_silently=False)
            item.status = EmailQueue.STATUS_SENT
            item.sent_at = timezone.now()
            item.attempts += 1
            item.last_error = ""
            item.save(update_fields=["status", "sent_at", "attempts", "last_error"])
            sent_count += 1
        except Exception as exc:
            item.status = EmailQueue.STATUS_FAILED
            item.attempts += 1
            item.last_error = str(exc)
            item.save(update_fields=["status", "attempts", "last_error"])
            failed_count += 1

    return {"sent": sent_count, "failed": failed_count}
