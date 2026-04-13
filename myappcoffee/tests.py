# delete_webhook.py
import telebot

TOKEN = '6648366599:AAF4ndqfgW4IsOnMzjFL9ZgocXWYeQIADAA'
bot = telebot.TeleBot(TOKEN)

# Удаляем вебхук
bot.delete_webhook()
print("✅ Вебхук удален!")

# Проверяем
info = bot.get_webhook_info()
print(f"Текущий вебхук: {info.url}")