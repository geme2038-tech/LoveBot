import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import json
import os
import traceback

# Включим логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен твоего бота
BOT_TOKEN = "8304459768:AAWD5WQtEBNhT_0vfMLsI9alH99xpU"

# База данных
user_data = {}  # {user_id: {'username': '...', 'liked': None, 'matched_with': None}}
pending_likes = {}  # {target_username: [(admirer_id, message)]}

# Файл для сохранения данных
DATA_FILE = "valentine_data.json"


def load_data():
    """Загружает данные из файла"""
    global user_data, pending_likes
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_data = data.get('user_data', {})
                # Конвертируем ключи обратно в int
                user_data = {int(k): v for k, v in user_data.items()}
                
                # Загружаем pending_likes
                pending_likes_data = data.get('pending_likes', {})
                pending_likes = {}
                for username, likes in pending_likes_data.items():
                    # Восстанавливаем список (admirer_id, message)
                    pending_likes[username] = [(int(admirer_id), msg) for admirer_id, msg in likes]
                
                logger.info(f"✅ Загружено {len(user_data)} пользователей и {sum(len(v) for v in pending_likes.values())} ожидающих валентинок")
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки данных: {e}")
        traceback.print_exc()


def save_data():
    """Сохраняет данные в файл"""
    try:
        # Конвертируем для JSON
        user_data_to_save = {str(k): v for k, v in user_data.items()}
        
        # Конвертируем pending_likes
        pending_likes_to_save = {}
        for username, likes in pending_likes.items():
            pending_likes_to_save[username] = [(str(admirer_id), msg) for admirer_id, msg in likes]
        
        data = {
            'user_data': user_data_to_save,
            'pending_likes': pending_likes_to_save
        }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 Данные сохранены")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения данных: {e}")


def escape_markdown(text):
    """Экранирует специальные символы Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    try:
        user = update.effective_user
        user_id = user.id
        username = user.username
        
        logger.info(f"👤 Пользователь @{username} (ID: {user_id}) запустил бота")

        # Сохраняем пользователя
        if user_id not in user_data:
            user_data[user_id] = {
                'username': username,
                'liked': None,
                'matched_with': None
            }
            save_data()
        
        # Ищем валентинки для этого пользователя
        found_valentines = []
        
        if username:
            # Ищем по точному username
            if username in pending_likes:
                found_valentines.extend(pending_likes[username])
                del pending_likes[username]
                save_data()
                logger.info(f"Найдено {len(found_valentines)} валентинок для @{username}")
        
        if found_valentines:
            context.user_data['pending_for_me'] = found_valentines
            await show_next_valentine(update, context, user_id)
        else:
            await update.message.reply_text(
                f"💘 Привет, {user.first_name}! Я Валентин-бот\n\n"
                f"Хочешь отправить анонимную валентинку?\n"
                f"Просто отправь мне @username человека и напиши сообщение в формате:\n"
                f"@username Твоё сообщение\n\n"
                f"Пример: @durov Ты мне очень нравишься!",
                parse_mode=None  # Убираем parse_mode
            )
    except Exception as e:
        logger.error(f"Ошибка в start: {e}")
        traceback.print_exc()
        await update.message.reply_text("❌ Произошла ошибка. Попробуй еще раз.")


async def show_next_valentine(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    """Показывает следующую валентинку"""
    try:
        if 'pending_for_me' in context.user_data and context.user_data['pending_for_me']:
            admirer_id, message = context.user_data['pending_for_me'].pop(0)
            
            admirer_username = user_data.get(admirer_id, {}).get('username', 'Неизвестно')
            
            keyboard = [
                [
                    InlineKeyboardButton("💕 Взаимно!", callback_data=f"match_{admirer_id}"),
                    InlineKeyboardButton("💔 Не взаимно", callback_data=f"reject_{admirer_id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем без Markdown разметки
            await update.message.reply_text(
                f"💌 У тебя есть анонимная валентинка!\n\n"
                f"{message}\n\n"
                f"Что ответишь?",
                reply_markup=reply_markup,
                parse_mode=None  # Убираем Markdown
            )
            
            if context.user_data['pending_for_me']:
                await update.message.reply_text(f"📨 У тебя есть ещё {len(context.user_data['pending_for_me'])} валентинок!")
        else:
            await update.message.reply_text(
                "💘 Все валентинки просмотрены! Хочешь отправить свою?\n"
                "Просто напиши @username и сообщение"
            )
    except Exception as e:
        logger.error(f"Ошибка в show_next_valentine: {e}")
        traceback.print_exc()
        await update.message.reply_text("❌ Произошла ошибка при показе валентинки.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает входящие сообщения"""
    try:
        admirer_id = update.effective_user.id
        admirer_username = update.effective_user.username
        text = update.message.text.strip()
        
        logger.info(f"📨 Сообщение от @{admirer_username}: {text}")

        # Проверяем формат: @username сообщение
        if not text.startswith('@'):
            await update.message.reply_text(
                "❌ Неправильный формат!\n"
                "Отправь сообщение в формате:\n"
                "@username Твоё сообщение\n\n"
                "Пример: @durov Привет, ты мне нравишься!",
                parse_mode=None
            )
            return

        # Разделяем username и сообщение
        parts = text.split(' ', 1)
        target_username_with_at = parts[0]
        target_username = target_username_with_at[1:]  # Убираем @
        
        if len(parts) < 2 or not parts[1]:
            await update.message.reply_text(
                "❌ Напиши ещё и сообщение!\n"
                "Пример: @durov Ты мне очень нравишься!"
            )
            return
        
        message = parts[1]

        # Проверка на самого себя
        if admirer_username and admirer_username.lower() == target_username.lower():
            await update.message.reply_text("❌ Нельзя отправить валентинку самому себе!")
            return

        # Ищем цель в базе по username
        target_id = None
        for uid, data in user_data.items():
            if data.get('username') and data['username'].lower() == target_username.lower():
                target_id = uid
                break

        # Сохраняем валентинку
        if target_username not in pending_likes:
            pending_likes[target_username] = []
        
        pending_likes[target_username].append((admirer_id, message))
        save_data()
        
        logger.info(f"💝 Валентинка сохранена для @{target_username}")

        # Если цель уже запускала бота, отправляем сразу
        if target_id:
            try:
                await notify_target(context, target_id, admirer_id, message, target_username)
                # Удаляем из pending, т.к. отправили
                pending_likes[target_username].remove((admirer_id, message))
                if not pending_likes[target_username]:
                    del pending_likes[target_username]
                save_data()
                
                await update.message.reply_text(
                    f"✅ Валентинка доставлена! ✨\n\n"
                    f"Кому: @{target_username}\n"
                    f"Сообщение: {message}\n\n"
                    f"Когда он ответит, я тебе сообщу!"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сразу: {e}")
                traceback.print_exc()
                # Получаем username бота безопасно
                bot_info = await context.bot.get_me()
                bot_username = bot_info.username
                
                await update.message.reply_text(
                    f"💌 Валентинка сохранена!\n\n"
                    f"Кому: @{target_username}\n"
                    f"Сообщение: {message}\n\n"
                    f"Я отправлю её, как только @{target_username} запустит бота!\n\n"
                    f"👆 Отправь ему эту ссылку:\n"
                    f"https://t.me/{bot_username}"
                )
        else:
            # Получаем username бота безопасно
            bot_info = await context.bot.get_me()
            bot_username = bot_info.username
            
            await update.message.reply_text(
                f"💌 Валентинка сохранена!\n\n"
                f"Кому: @{target_username}\n"
                f"Сообщение: {message}\n\n"
                f"📨 Она будет доставлена, как только @{target_username} напишет мне!\n\n"
                f"👆 Отправь ему эту ссылку:\n"
                f"https://t.me/{bot_username}"
            )

    except Exception as e:
        logger.error(f"Ошибка в handle_message: {e}")
        traceback.print_exc()
        await update.message.reply_text("❌ Произошла ошибка. Попробуй еще раз.")


async def notify_target(context, target_id, admirer_id, message, target_username):
    """Отправляет уведомление цели"""
    try:
        keyboard = [
            [
                InlineKeyboardButton("💕 Взаимно!", callback_data=f"match_{admirer_id}"),
                InlineKeyboardButton("💔 Не взаимно", callback_data=f"reject_{admirer_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Отправляем без Markdown разметки
        await context.bot.send_message(
            chat_id=target_id,
            text=f"💌 У тебя анонимная валентинка!\n\n"
                 f"{message}\n\n"
                 f"Что ответишь?",
            reply_markup=reply_markup,
            parse_mode=None  # Убираем Markdown
        )
        logger.info(f"✅ Уведомление отправлено @{target_username}")
    except Exception as e:
        logger.error(f"Ошибка в notify_target: {e}")
        raise


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает нажатия кнопок"""
    try:
        query = update.callback_query
        await query.answer()
        
        target_id = query.from_user.id
        target_username = query.from_user.username
        data = query.data
        
        logger.info(f"🔘 Нажата кнопка {data} от @{target_username}")

        if data.startswith('match_'):
            admirer_id = int(data.split('_')[1])
            await handle_match(query, context, target_id, target_username, admirer_id)
            
        elif data.startswith('reject_'):
            admirer_id = int(data.split('_')[1])
            await handle_reject(query, context, target_id, target_username, admirer_id)
    except Exception as e:
        logger.error(f"Ошибка в button_callback: {e}")
        traceback.print_exc()
        await query.edit_message_text("❌ Произошла ошибка.")


async def handle_match(query, context, target_id, target_username, admirer_id):
    """Обрабатывает взаимность"""
    try:
        admirer_username = user_data.get(admirer_id, {}).get('username', 'Неизвестно')

        if admirer_id in user_data and target_id in user_data:
            # Сохраняем мэтч
            user_data[admirer_id]['matched_with'] = target_id
            user_data[target_id]['matched_with'] = admirer_id
            save_data()

            # Уведомляем адмирата
            await context.bot.send_message(
                chat_id=admirer_id,
                text=f"🎉 ЭТО ВЗАИМНО! 🎉\n\n"
                     f"Твоя валентинка понравилась @{target_username}!\n"
                     f"Он(а) тоже нажал(а) «Взаимно»!\n\n"
                     f"💬 Начинайте общаться: @{target_username}",
                parse_mode=None  # Убираем Markdown
            )

            # Уведомляем цель
            await query.edit_message_text(
                text=f"🎉 ЭТО ВЗАИМНО! 🎉\n\n"
                     f"Тот, кто отправил тебе валентинку — @{admirer_username}!\n\n"
                     f"💬 Напиши ему: @{admirer_username}"
            )
            logger.info(f"💕 Мэтч создан: @{admirer_username} и @{target_username}")
        else:
            await query.edit_message_text(text="❌ Ошибка данных пользователей.")
    except Exception as e:
        logger.error(f"Ошибка в handle_match: {e}")
        traceback.print_exc()
        await query.edit_message_text(text="❌ Произошла ошибка при создании мэтча.")


async def handle_reject(query, context, target_id, target_username, admirer_id):
    """Обрабатывает отказ"""
    try:
        # Уведомляем адмирата об отказе
        try:
            await context.bot.send_message(
                chat_id=admirer_id,
                text="💔 К сожалению, твоя валентинка не нашла отклика...\n"
                     "Не расстраивайся! Впереди много новых знакомств! 🌟"
            )
        except:
            pass

        await query.edit_message_text(
            text="💔 Ты отклонил(а) эту валентинку.\n"
                 "Пользователь не узнает, кто ты."
        )
        logger.info(f"💔 Отказ от @{target_username}")
    except Exception as e:
        logger.error(f"Ошибка в handle_reject: {e}")
        traceback.print_exc()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    try:
        await update.message.reply_text(
            "💌 Как отправить валентинку:\n"
            "1. Напиши: @username Твоё сообщение\n"
            "2. Я сохраню валентинку\n"
            "3. Когда человек запустит бота, он её получит\n"
            "4. Он увидит кнопки:\n"
            "   💕 Взаимно - вы узнаете друг о друге\n"
            "   💔 Не взаимно - отказ останется анонимным\n\n"
            "✨ Валентинки сохраняются навсегда, пока не будут доставлены!",
            parse_mode=None
        )
    except Exception as e:
        logger.error(f"Ошибка в help: {e}")
        await update.message.reply_text("❌ Произошла ошибка.")


def main():
    """Запуск бота"""
    try:
        # Загружаем сохраненные данные
        load_data()
        
        print("🚀 Создание приложения...")
        application = Application.builder().token(BOT_TOKEN).build()

        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_callback))

        print("✅ Бот запущен... Валентинки готовы к отправке! 💘")
        print(f"📊 Статистика: {len(user_data)} пользователей, {sum(len(v) for v in pending_likes.values())} ожидающих валентинок")
        print("📝 Формат: @username сообщение")
        print("🔄 Нажми Ctrl+C для остановки")
        
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"Критическая ошибка в main: {e}")
        traceback.print_exc()


if __name__ == '__main__':

    main()
