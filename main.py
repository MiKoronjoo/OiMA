import logging
import enum
import sqlite3

from telegram import Update, Message, InlineQueryResultCachedVoice, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery, InlineQuery
from telegram.ext import Updater, CallbackContext, MessageHandler, InlineQueryHandler, CallbackQueryHandler
from config import BOT_TOKEN, DB_PATH


def exe_query(query):
    con_obj = sqlite3.connect(DB_PATH)
    courser = con_obj.execute(query)
    res = courser.fetchall()
    con_obj.commit()
    con_obj.close()
    return res


class State(enum.Enum):
    MAIN = 0
    VOICE = 1
    TEXT = 2
    ADMIN = 3
    ADD_ADMIN = 4
    REM_ADMIN = 5


class Admin:
    def __init__(self, telegram_id):
        self.id = telegram_id

    @property
    def state(self):
        return exe_query(f'SELECT state FROM Admin WHERE id = {self.id};')[0][0]

    @state.setter
    def state(self, value):
        exe_query(f'UPDATE Admin SET state = {value} WHERE id = {self.id};')

    def add_voice(self, file_id):
        if file_id not in (file_id for file_id, _, _ in get_voices()):
            exe_query(f"INSERT INTO Voice (file_id) VALUES ('{file_id}');")
        exe_query(f"UPDATE Admin SET voice_file_id = '{file_id}' WHERE Admin.id = {self.id};")

    def add_text(self, text):
        exe_query(f"UPDATE Voice SET text = '{text}'"
                  f"WHERE Voice.file_id = (SELECT voice_file_id FROM Admin WHERE id = {self.id});")


def get_admin(telegram_id):
    if exe_query(f'SELECT * FROM Admin WHERE Admin.id = {telegram_id}'):
        return Admin(telegram_id)


def get_voices(text=None):
    if text is None:
        return exe_query(f'SELECT * FROM Voice;')
    return exe_query(f"SELECT * FROM Voice WHERE Voice.text LIKE '%{text}%'")


def get_text(vid):
    return exe_query(f'SELECT text FROM Voice WHERE id = {vid};')[0][0]


def on_message(update: Update, context: CallbackContext):
    admin = get_admin(update.effective_user.id)
    if not admin:
        return
    msg: Message = update.effective_message
    if msg.voice:
        admin.add_voice(msg.voice.file_id)
        admin.add_text(msg.caption)
        context.bot.send_message(update.effective_chat.id, 'Done!')
    else:
        context.bot.send_message(update.effective_chat.id, 'Send a voice!')


def on_inline_query(update: Update, context: CallbackContext):
    query: InlineQuery = update.inline_query
    results = [InlineQueryResultCachedVoice(id=id,
                                            voice_file_id=file_id,
                                            title=text,
                                            reply_markup=InlineKeyboardMarkup(
                                                [[InlineKeyboardButton(text='text',
                                                                       callback_data=id)]])
                                            ) for file_id, text, id in get_voices(query.query)]
    context.bot.answer_inline_query(query.id, results)


def on_callback_query(update: Update, context: CallbackContext):
    query: CallbackQuery = update.callback_query
    context.bot.answer_callback_query(query.id, get_text(query.data), show_alert=True)


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    message_handler = MessageHandler(None, on_message)
    dispatcher.add_handler(message_handler)
    inline_handler = InlineQueryHandler(on_inline_query)
    dispatcher.add_handler(inline_handler)
    callback_handler = CallbackQueryHandler(on_callback_query)
    dispatcher.add_handler(callback_handler)

    updater.start_polling()
    print('START')
