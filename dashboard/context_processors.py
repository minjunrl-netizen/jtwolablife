def notifications(request):
    if request.user.is_authenticated:
        from dashboard.models import Notification
        notifs = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notifications': notifs[:10],
            'unread_count': notifs.count(),
        }
    return {}
