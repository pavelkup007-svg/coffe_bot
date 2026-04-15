#!/usr/bin/env python
# run_bot.py - Запуск телеграм бота с использованием Django моделей

import os
import sys
import time
import logging
import datetime
from pathlib import Path
from flask import Flask, request
import threading
app = Flask(__name__)
# Добавляем путь к проекту (на случай, если скрипт запущен не из корня)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Указываем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'coffee.settings')

# Инициализируем Django
import django

django.setup()

# Теперь можно импортировать все из views.py
from myappcoffee.models import User  # Убедитесь, что путь правильный
from django.utils import timezone
from django.db.models import Sum, Max, Min

import telebot
from telebot import apihelper

# Настройка логирования
logging.basicConfig(level=logging.INFO)

TOKEN = '7272267982:AAEkQFtJQf7Ia5zls7WJBRgHIBssOLPTNOw'
# TOKEN = '6648366599:AAF4ndqfgW4IsOnMzjFL9ZgocXWYeQIADAA'

# Стандартное создание бота (для локальной разработки)
bot = telebot.TeleBot(TOKEN)

ADMIN_USER_IDS = [740586983, 372042591, 211600094]
user_sessions = {}


# ============= ВСЕ ВАШИ ОБРАБОТЧИКИ ИЗ VIEWS.PY =============

@bot.message_handler(commands=['send_message'])
def handle_send_message(message):
    user_id = message.from_user.id

    # Проверяем, что пользователь имеет права администратора
    if user_id in ADMIN_USER_IDS:
        # Спрашиваем у администратора ID пользователей
        msg = bot.reply_to(message, "Введите ID пользователей через запятую")
        bot.register_next_step_handler(msg, get_user_ids)
    else:
        bot.reply_to(message, "У вас нет прав для выполнения этой команды.")

    logging.info(f"Received /send_message command from user_id: {user_id}")


# Получаем список ID пользователей и запрашиваем текст сообщения
def get_user_ids(message):
    try:
        # Преобразуем введенные значения в список ID
        user_ids = [int(user_id.strip()) for user_id in message.text.split(",")]

        # Сохраняем user_ids для использования в следующем шаге
        user_sessions[message.from_user.id] = {'target_user_ids': user_ids}

        # Спрашиваем текст сообщения
        msg = bot.reply_to(message, "Введите текст сообщения.")
        bot.register_next_step_handler(msg, send_message_to_users)

    except ValueError:
        bot.reply_to(message, "ID пользователей должны быть числами, разделёнными запятыми. Попробуйте снова.")
        return


# Отправляем сообщение указанным пользователям
def send_message_to_users(message):
    # Получаем целевые ID пользователей из сессии
    target_user_ids = user_sessions[message.from_user.id].get('target_user_ids')

    # Получаем текст сообщения
    text_to_send = message.text

    successful_sends = []
    failed_sends = []

    for user_id in target_user_ids:
        try:
            # Отправляем сообщение каждому пользователю с указанным ID
            bot.send_message(user_id, text_to_send)
            successful_sends.append(user_id)
        except Exception as e:
            failed_sends.append(user_id)
            logging.error(f"Ошибка при отправке сообщения пользователю с ID {user_id}: {e}")

    # Сообщаем администратору о результате отправки
    if successful_sends:
        bot.reply_to(message,
                     f"Сообщение успешно отправлено пользователям с ID: {', '.join(map(str, successful_sends))}.")
    if failed_sends:
        bot.reply_to(message,
                     f"Не удалось отправить сообщение пользователям с ID: {', '.join(map(str, failed_sends))}.")

    # Очищаем сессию
    del user_sessions[message.from_user.id]


# Функция для создания клавиатуры с кнопками
def get_markup_for_user(user_id):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Кнопки доступные только для администраторов
    if user_id in ADMIN_USER_IDS:
        markup.add(telebot.types.KeyboardButton('Cup'))
        markup.add(telebot.types.KeyboardButton('Отчет'))
        markup.add(telebot.types.KeyboardButton('Рассылка'))  # Новая кнопка рассылки

    # Кнопка доступная всем пользователям
    markup.add(telebot.types.KeyboardButton('Платежи'))

    return markup


@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    logging.info(f"Received /start command from user_id: {user_id}")

    # Проверка пользователя в базе данных
    try:
        user = User.objects.get(user_id=user_id)
        markup = get_markup_for_user(user_id)  # Создаем клавиатуру
        bot.send_message(message.chat.id, f'Пользователь определен: {user.first_name}', reply_markup=markup)
        bot.reply_to(message, "Пожалуйста, введите пароль.")
        user_sessions[user_id] = {
            'state': 'awaiting_password',
            'username': username,
            'first_name': first_name,
            'attempts': 0
        }
    except User.DoesNotExist:
        # Запись user_id в текстовый файл
        with open('unknown_users.txt', 'a', encoding='utf-8') as f:
            f.write(f"{user_id} - {username}\n")
        bot.reply_to(message, "Пользователь не определен")


@bot.message_handler(
    func=lambda message: user_sessions.get(message.from_user.id, {}).get('state') == 'awaiting_password')
def handle_password(message):
    user_id = message.from_user.id
    input_password = message.text

    logging.info(f"Received password from user_id: {user_id}")

    # Получаем пользователя и его данные из сессии
    session = user_sessions.get(user_id)

    if session:
        try:
            user = User.objects.get(user_id=user_id)
            if input_password == user.password:
                user.update_cups_today()
                with open('user_data.txt', 'a', encoding='utf-8') as f:
                    f.write(
                        f"{user_id}, {session['username']}, {session['first_name']}, количество чашек={user.cups}, {(timezone.now() + datetime.timedelta(hours=3)).strftime('%d.%m.%Y %H:%M:%S')}\n")
                bot.reply_to(message,
                             f"Пароль верен. Количество чашек обновлено, количество: {user.cups}, стоимость к оплате: {format(user.amount_due, '.2f')}.руб")
                bot.send_message(message.chat.id, f'Для повторной записи, нажмите /start')
                # Завершение сессии
                del user_sessions[user_id]
            else:
                session['attempts'] += 1
                if session['attempts'] < 2:
                    bot.reply_to(message, "Пароль неверен. Попробуйте еще раз.")
                    bot.send_message(message.chat.id, f'Для повторной попытки, нажмите /start')
                else:
                    bot.reply_to(message, "Вы исчерпали все попытки. Попробуйте снова позже.")
                    del user_sessions[user_id]
        except User.DoesNotExist:
            bot.reply_to(message, "Пользователь не найден. Пожалуйста, нажмите /start, чтобы попробовать снова.")
            bot.send_message(message.chat.id, f'/start')


@bot.message_handler(func=lambda message: message.text == 'Cup' and message.from_user.id in ADMIN_USER_IDS)
def handle_cup_message(message):
    today = timezone.now().date()  # Получаем сегодняшнюю дату

    # Считаем общее количество чашек для всех пользователей за сегодня
    total_cups_today = User.objects.filter(last_cup_date=today).aggregate(total=Sum('cups_today'))['total'] or 0

    # Находим максимальное и минимальное количество чашек за день
    max_cups = User.objects.filter(last_cup_date=today).aggregate(max_cups=Max('cups_today'))['max_cups'] or 0
    min_cups = User.objects.filter(last_cup_date=today).aggregate(min_cups=Min('cups_today'))['min_cups'] or 0

    # Находим всех пользователей с максимальным количеством чашек
    max_cups_users = User.objects.filter(last_cup_date=today, cups_today=max_cups)

    # Находим всех пользователей с минимальным количеством чашек
    min_cups_users = User.objects.filter(last_cup_date=today, cups_today=min_cups)

    # Формируем информацию о пользователях
    max_cups_info = "Больше всего кофе выпили:\n" + "\n".join(
        [f"{user.first_name} ({user.cups_today} чашек)" for user in max_cups_users]) if max_cups_users else "Нет данных"
    min_cups_info = "Меньше всего кофе выпили:\n" + "\n".join(
        [f"{user.first_name} ({user.cups_today} чашек)" for user in min_cups_users]) if min_cups_users else "Нет данных"

    # Формируем итоговое сообщение
    response_message = (
        f"Сегодняшнее общее количество чашек: {total_cups_today}\n\n"
        f"{max_cups_info}\n"
        f"{min_cups_info}"
    )

    bot.reply_to(message, response_message)


@bot.message_handler(func=lambda message: message.text == 'Платежи')
def handle_payment_message(message):
    user_id = message.from_user.id
    try:
        user = User.objects.get(user_id=user_id)
        # Получаем сумму к оплате и залог из базы данных
        amount_due = user.amount_due
        deposit = user.deposit

        # Формируем сообщение с информацией об оплате
        payment_message = (
            f"User ID: {user.user_id}\n"
            f"First name: {user.first_name}\n"
            f"Кол-во чашек: {user.cups}\n"
            f"Сумма к оплате: {amount_due} руб.\n"
            f"Депозит: {deposit} руб.\n"
            f"Остаток: {deposit - amount_due} руб."
        )

        bot.reply_to(message, payment_message)
        bot.send_message(message.chat.id, "Нужна ли вам детализация? Ответьте 'да' или 'нет'.")
        user_sessions[user_id] = {
            'state': 'awaiting_details'
        }

    except User.DoesNotExist:
        bot.reply_to(message, "Пользователь не найден. Пожалуйста, нажмите /start, чтобы попробовать снова.")


@bot.message_handler(
    func=lambda message: user_sessions.get(message.from_user.id, {}).get('state') == 'awaiting_details')
def handle_details_request(message):
    user_id = message.from_user.id
    user_response = message.text.lower()

    if user_response == 'да':
        try:
            # Создаем файл с детализацией
            with open('user_data.txt', 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Отбираем строки, которые соответствуют user_id
            user_data_lines = [line for line in lines if line.startswith(f'{user_id},')]

            if user_data_lines:
                details_filename = f'details_{user_id}.txt'
                with open(details_filename, 'w', encoding='utf-8') as details_file:
                    details_file.writelines(user_data_lines)

                # Отправляем файл пользователю
                with open(details_filename, 'rb') as details_file:
                    bot.send_document(message.chat.id, details_file)
            else:
                bot.reply_to(message, "Детализация данных не найдена.")

        except Exception as e:
            bot.reply_to(message, "Произошла ошибка при получении детализации.")
            logging.error(f"Error generating details file: {e}")

    elif user_response == 'нет':
        bot.reply_to(message, "Детализация не будет предоставлена.")

    # Завершаем сессию ожидания
    if user_id in user_sessions:
        del user_sessions[user_id]


@bot.message_handler(
    func=lambda message: message.text == 'Отчет' and message.from_user.id in [740586983, 372042591, 211600094])
def handle_report_message(message):
    user_id = message.from_user.id

    try:
        # Получаем все данные пользователей
        users = User.objects.all()

        # Формируем строки для отчета
        report_lines = []
        for user in users:
            money = []
            different = user.deposit - user.amount_due
            if different >= 20:
                money.append('не сдает')
            elif different <= 0:
                money.append('сдает в двойном размере')
            else:
                money.append('сдает')

            report_lines.append(
                f"{user.user_id}, {user.username}, {user.first_name}, cups = {user.cups}, {user.last_cup_date}, deposit = {user.deposit}, price = {user.amount_due}, {money}, ostatok = {user.deposit - user.amount_due}\n")

        # Сохраняем отчет в файл
        report_filename = f'report_{timezone.now().strftime("%Y%m%d_%H%M%S")}.txt'
        with open(report_filename, 'w', encoding='utf-8') as report_file:
            report_file.writelines(report_lines)

        # Отправляем файл пользователю
        with open(report_filename, 'rb') as report_file:
            bot.send_document(message.chat.id, report_file)

    except Exception as e:
        bot.reply_to(message, "Произошла ошибка при создании отчета.")
        logging.error(f"Error generating report file: {e}")


@bot.message_handler(func=lambda message: message.text == 'Рассылка' and message.from_user.id in [740586983, 211600094])
def handle_broadcast(message):
    user_id = message.from_user.id
    logging.info(f"Received broadcast request from user_id: {user_id}")

    # Запрашиваем подтверждение
    msg = bot.reply_to(message, "Вы уверены, что хотите сделать рассылку всем пользователям? (да/нет)")
    bot.register_next_step_handler(msg, confirm_broadcast)


def confirm_broadcast(message):
    user_id = message.from_user.id
    response = message.text.lower()

    if response == 'да':
        try:
            # Получаем всех пользователей из базы данных
            all_users = User.objects.all()
            successful_sends = 0
            failed_sends = []

            # Текст сообщения для рассылки
            broadcast_text = (
                "Коллеги, сегодня день аванса.\n\n"
                "Прошу проверить в телеграм-боте свой депозит по кофе.\n\n"
                "Минимальный остаток – 20 рублей.\n\n"
                "Убедительная просьба – сдать наличные деньги Тимуру."
            )

            for user in all_users:
                if user.user_id:  # Проверяем, что user_id не None
                    try:
                        bot.send_message(user.user_id, broadcast_text)
                        successful_sends += 1
                    except Exception as e:
                        failed_sends.append(user.user_id)
                        logging.error(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

            # Отправляем отчет администратору
            report_message = (
                f"Рассылка завершена:\n"
                f"Успешно отправлено: {successful_sends}\n"
                f"Не удалось отправить: {len(failed_sends)}"
            )

            if failed_sends:
                report_message += f"\n\nСписок ID, кому не удалось отправить:\n{', '.join(map(str, failed_sends))}"

            bot.send_message(user_id, report_message)

        except Exception as e:
            bot.reply_to(message, f"Произошла ошибка при рассылке: {e}")
            logging.error(f"Broadcast error: {e}")
    else:
        bot.send_message(user_id, "Рассылка отменена.")
@app.route('/')
def health():
    """Эндпоинт для пинга от UptimeRobot"""
    return "Bot is alive", 200

def run_web():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    """Резервный keep-alive"""
    ADMIN_ID = 740586983
    while True:
        try:
            # Отправляем сообщение только если бот не спал
            bot.send_message(ADMIN_ID, "🟢 Бот работает", disable_notification=True)
            time.sleep(600)
        except:
            time.sleep(60)

# Запускаем оба механизма
threading.Thread(target=run_web, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()        


# ============= КОНЕЦ ОБРАБОТЧИКОВ =============

if __name__ == '__main__':
    logging.info("Starting bot polling...")

    # Бесконечный цикл с перезапуском при ошибках
    while True:
        try:
            # Запускаем бота
            bot.polling(
                none_stop=True,  # Не падать при ошибках
                timeout=20,  # Таймаут
                interval=2  # Интервал между запросами
            )
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
            sys.exit(0)
        except Exception as e:
            logging.error(f"Bot crashed with error: {e}")
            logging.info("Restarting bot in 10 seconds...")
            time.sleep(10)
