from django.apps import AppConfig
import threading


class MyAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'myappcoffee'

    # def ready(self):
    #     from .views import start_bot
    #     threading.Thread(target=start_bot).start()