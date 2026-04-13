# views.py - Оставляем только Django views (для веб-части, если она нужна)
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Если нужен простой веб-интерфейс для проверки работы
def index(request):
    return HttpResponse("""
    <h1>Coffee Bot</h1>
    <p>Бот работает в отдельном процессе.</p>
    <p>Для запуска бота выполните: python run_bot.py</p>
    """)

# Опционально: эндпоинт для проверки статуса бота
def bot_status(request):
    return JsonResponse({
        'status': 'running',
        'message': 'Bot is running separately'
    })

# Опционально: эндпоинт для вебхука (если перейдете на вебхуки в будущем)
@csrf_exempt
def webhook(request):
    """
    Эндпоинт для вебхука Telegram.
    Используется только если вы переключитесь на вебхуки вместо polling.
    """
    if request.method == 'POST':
        try:
            # Здесь будет обработка вебхука
            # Пока просто логируем
            logging.info("Received webhook request")
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            logging.error(f"Webhook error: {e}")
            return JsonResponse({'status': 'error'}, status=500)
    return JsonResponse({'status': 'ready'})

# Опционально: админ-панель или другие Django views
# Если у вас были другие views, оставьте их здесь