from django.http import JsonResponse


def health(request):
    """Public health check — no auth. Use from mobile browser to verify backend is reachable."""
    return JsonResponse({"ok": True})
