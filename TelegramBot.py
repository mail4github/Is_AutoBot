import sys
import base64
import requests  # pip install requests
import json
import os
import time
from telegram import Update  # pip install python-telegram-bot
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes, filters, MessageHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import KeyboardButton, ReplyKeyboardMarkup
from pathlib import Path
import threading
import asyncio
from datetime import datetime
import subprocess
import hashlib
from PIL import Image  # python3 -m pip install pillow
import fnmatch
import random
import io


thread_activity_interval = 3  # seconds
checking_results_in_thread_activity_every_secs = 60  # seconds
run_script_after_secs = 50
truncate_message_to_symbols = 900
max_errors_to_halt = 1
number_of_errors = 0
debug_mode = False
users_arr = {}
current_active_loop = None
languages_arr = []
last_time_of_thread_activity = 0
last_api_error = ''
last_api_message = ''

def fill_in_user_arr(telegram_userid: int, user_firstname='', user_lastname='', username='', language_code=''):
    global users_arr
    try:
        users_arr[telegram_userid] = {
            'text_mode': '',
        }
        '''res = get_api_values({
            'custom_command': 'user_check_in',
            'firstname': base64.b64encode(user_firstname.encode('utf-8')).decode("utf-8"),
            'lastname': base64.b64encode(user_lastname.encode('utf-8')).decode("utf-8"),
            'telegram_username': username,
            'language_code': language_code,
        })
        if res != False:
            users_arr[telegram_userid] = {
                'text_mode': res['text_mode'] if 'text_mode' in res and res['text_mode'] != None else users_arr[telegram_userid]['text_mode'] if telegram_userid in users_arr and 'text_mode' in users_arr[telegram_userid] else '',
            }
            pass'''

    except BaseException as e:
        print(f'exception in fill_in_user_arr {e}')
        pass

def get_user_record(update: Update, force_update_from_DB: bool = False):
    global users_arr

    if not update.effective_user.id in users_arr or force_update_from_DB:
        user_firstname = ''
        user_lastname = ''
        username = ''
        language_code = ''

        try:
            if not update.effective_user.first_name is None:
                user_firstname = update.effective_user.first_name
        except:
            user_firstname = ''
            pass
        try:
            if not update.effective_user.last_name is None:
                user_lastname = update.effective_user.last_name
        except:
            user_lastname = ''
            pass
        try:
            if not update.effective_user.username is None:
                username = update.effective_user.username
        except:
            username = ''
            pass
        try:
            if not update.effective_user.language_code is None:
                language_code = update.effective_user.language_code
        except:
            language_code = 'ru'
            pass
        try:
            fill_in_user_arr(update.effective_user.id, user_firstname, user_lastname, username, language_code)
            save_log(f'Connected user: id={update.effective_user.id}, {user_firstname=}, {user_lastname=}, {username=}')

            '''get_api_values(update.effective_user.id, {
                'custom_command': 'user_logged_in'
            })'''

        except BaseException as e:
            print(f'exception in get_user_record {e}')
            save_log('pid:' + str(os.getpid()) + ', ' + f'exception in get_user_record {e}')
            pass

    return users_arr[update.effective_user.id]

def save_log(log_message: str = '', log_file_path: str = ''):
    global params_arr

    if len(log_file_path) == 0:
        if 'log_file_name' in params_arr:
            log_file_path = Path(os.path.dirname(os.path.realpath(__file__)) + '/' + params_arr['log_file_name'])
        else:
            log_file_path = os.path.basename(__file__) + '.log'

    # if log file is big then raname it and start new log
    try:
        log_file_size = os.stat(log_file_path).st_size
        if log_file_size > 1000000:
            file_name_to_save_old_log = str(log_file_path) + '.old'
            try:
                os.remove(file_name_to_save_old_log)
            except BaseException as e:
                pass
            os.rename(log_file_path, file_name_to_save_old_log)
    except BaseException as e:
        pass

    now = datetime.now()
    if os.path.exists(log_file_path):
        append_write = 'a'  # append if already exists
    else:
        append_write = 'w'  # make a new file if not
    f = open(log_file_path, append_write, encoding="utf8")

    f.write(f'{now.strftime("%d/%m/%Y %H:%M")} {log_message}\r\n')
    f.close()

def save_activity_file_for_watchdog():
    activity_file_for_watchdog = os.path.realpath(__file__) + '.watchdog'
    try:
        get_api_values({
            'custom_command': 'i_am_alive',
            'program_name': params_arr['TOKEN'].encode('utf-8').hex(),
            'program_description': params_arr['bot_username'],
        })
    except BaseException as e:
        pass
    try:
        js = Path(activity_file_for_watchdog).read_text()
        watchdog_arr = json.loads(js)
    except BaseException as e:
        pass

    try:
        os.remove(activity_file_for_watchdog)
    except BaseException as e:
        pass

    try:
        f = open(activity_file_for_watchdog, "x")
        f.write('{' + f'"time":{str(round(time.time()))}, "pid":{os.getpid()} ' + '}')
        f.close()
    except BaseException as e:
        pass


def get_api_values(post_data):
    global params_arr, last_api_error, last_api_message

    url = params_arr['url'] + 'custom_api/'

    post_data['email'] = params_arr['api_email']
    post_data['bot_username'] = params_arr['bot_username']

    token = params_arr['api_hash']
    x = datetime.now()
    token = token + x.strftime("%Y-%m-%d")
    post_data['token'] = hashlib.md5(token.encode('utf-8')).hexdigest()

    reqst = requests.post(url, data=post_data)
    if reqst.ok:
        answer_arr = reqst.json()
        if answer_arr and answer_arr != None and len(answer_arr) > 0:
            if answer_arr['success']:
                return answer_arr["values"]
            if 'error_code' in answer_arr and len(answer_arr['error_code']):
                last_api_error = answer_arr['error_code']
                last_api_message = answer_arr['message']
                save_log(f'get_api_values error: {last_api_error}, {last_api_message}')
    return False


def core_api_request(telegram_userid, command, post_data={}):
    global params_arr, last_api_error, last_api_message

    url = params_arr['url'] + command

    post_data['user_email'] = telegram_userid

    token = hashlib.md5(str(telegram_userid).encode('utf-8')).hexdigest()
    token = str(token) + params_arr['api_salt']
    token = hashlib.md5(token.encode('utf-8')).hexdigest()
    x = datetime.now()
    token = token + x.strftime("%Y-%m-%d")
    post_data['token'] = hashlib.md5(token.encode('utf-8')).hexdigest()

    reqst = requests.post(url, data=post_data)
    if reqst.ok:
        answer_arr = reqst.json()
        if answer_arr and answer_arr != None and len(answer_arr) > 0:
            if answer_arr['success']:
                return answer_arr["values"]
            if 'error_code' in answer_arr:
                last_api_error = answer_arr['error_code']
                last_api_message = answer_arr['message']
                save_log(f'core_api_request error: {last_api_error}, {last_api_message}')
    return False


def set_text_mode(update: Update, mode: str = ''):
    global users_arr

    if update is None:
        return False

    get_user_record(update)
    if update.effective_user.id in users_arr:
        users_arr[update.effective_user.id]['text_mode'] = mode

async def send_mess_from_thread(
        application,
        userid,
        msg: str,
        menu=None,
        no_sound: bool = False,
        image=None,
        its_video=False
):
    global params_arr

    try:
        if image != None:
            if its_video:
                await application.bot.send_video(
                    chat_id=userid,
                    video=image,
                    caption=msg,
                    parse_mode='HTML',
                    reply_markup=menu if menu != None else InlineKeyboardMarkup([])
                    , disable_notification=no_sound
                )
            else:
                await application.bot.send_photo(
                    chat_id=userid,
                    photo=image,
                    caption=msg,
                    parse_mode='HTML',
                    reply_markup=menu if menu != None else InlineKeyboardMarkup([])
                    , disable_notification=no_sound
                )
        else:
            await application.bot.send_message(
                chat_id=userid,
                text=msg,
                parse_mode = 'HTML',
                reply_markup=menu if menu != None else InlineKeyboardMarkup([])
                , disable_notification=no_sound
                , disable_web_page_preview=True
            )
        save_log(f'Message from thread sent to user: {str(userid)}')
        return True
    except BaseException as e:
        save_log('pid:' + str(os.getpid()) + ', exception in send_mess_from_thread: ' + str(e))
        save_log('Userid: ' + str(userid))

        if 'bot was blocked' in str(e.message) or 'Chat not found' in str(e.message) or 'Forbidden' in str(e.message):
            x = datetime.now()
            core_api_request(userid, 'user_disable_enable_account', {
                'disable': '1',
                'cancel_all_transactions': '1',
                'note': f"Cancelled by {params_arr['bot_username']} on " + x.strftime("%Y-%m-%d")
            })
        print(f'\033[93mexception in send_mess_from_thread {e}, userid: ', userid, ', message: ', msg, '\033[0m')
        number_of_errors += 1
        pass
    return False


def thread_activity(application):
    global users_arr, current_active_loop, last_time_of_thread_activity, number_of_errors, channel_language

    thread_is_active = True
    while thread_is_active:
        try:
            if number_of_errors > max_errors_to_halt:
                save_log(f'Abort app because errors = {str(number_of_errors)}')
                try:
                    subprocess.run(['kill', str(os.getpid())])
                except BaseException as e:
                    print(f'\033[93m exception in thread_activity {e}\033[0m')
                    pass

            time.sleep(thread_activity_interval)

            save_activity_file_for_watchdog()

            # ask for a messages to post on channel
            res = get_api_values({
                'custom_command': 'get_message_for_posting',
            })
            if res != False and len(res) > 0 and 'message' in res and len(res['message']) > 0:
                sent_to_channel = params_arr['sent_to_channel']
                if 'sent_to_channel' in res and len(res['sent_to_channel']):
                    sent_to_channel = res['sent_to_channel']

                asyncio.run_coroutine_threadsafe(
                    send_mess_from_thread(
                        application,
                        userid = '@' + sent_to_channel,
                        msg = res['message']
                    ),
                    current_active_loop
                )    
                
            time.sleep(thread_activity_interval)
            
        except BaseException as e:
            save_log('pid:' + str(os.getpid()) + ', exception in thread_activity: ' + str(e))

            lineno = -1
            fname = 'unknown'
            try:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                lineno = exc_tb.tb_lineno
            except:
                pass
            save_log('pid:' + str(os.getpid()) + ', ' + f'Exception in thread_activity {e}, source line number: {lineno}, file: {fname}')
            print(
                f'\033[93mexception in thread_activity {e}, source line number: {lineno}, file: {fname}\033[0m')
            number_of_errors += 1
            pass


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global users_arr

    get_user_record(update)
    set_text_mode(update)

    try:
        await update.message.reply_text(get_help_text(), parse_mode='HTML')
        return True

    except BaseException as e:
        print(f'\033[93m exception in start {e}\033[0m')
        save_log('pid:' + str(os.getpid()) + ', ' + f'Exception in start: {e}')
        pass

def get_help_text():
    global languages_arr

    commands_list = ''
    for command_item in commands_arr:
        if 'command_' + command_item[0] + '_description' in languages_arr:
            commands_list = commands_list + '/' + command_item[0] + ' - ' + languages_arr['command_' + command_item[0] + '_description'][channel_language] + '.\n'

    return languages_arr['help1'][channel_language].format(bot_username=params_arr['bot_username'], commands_list=commands_list)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command_arr: list = None) -> None:
    await update.effective_message.reply_text(
        get_help_text(),
        parse_mode='HTML', 
        disable_notification=True
    )

async def enter_a_text(update: Update, context: ContextTypes.DEFAULT_TYPE, command_arr: list = None):

    set_text_mode(update, 'enter_a_text')

    await update.effective_message.reply_text(
        languages_arr['enter_a_text'][channel_language],
        parse_mode='HTML'
        , disable_notification=True
    )

async def message_handler_function(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global last_api_error, last_api_message
    
    user_record = get_user_record(update)

    if len(user_record['text_mode']):
        await send_a_text(update, context, ['', user_record['text_mode']])
        
    set_text_mode(update, '')

    
def error_handler_function(update, context):
    global number_of_errors

    save_log('pid:' + str(os.getpid()) + ', error_handler_function: ' + str(context.error))

    print(f'\033[91m error \033[0m')

    number_of_errors = number_of_errors + 1

    if number_of_errors > max_errors_to_halt:
        print(f"\033[91m Program shutdown \033[0m")
        save_log('pid:' + str(os.getpid()) + ', Program shutdown')
        try:
            subprocess.run(['kill', str(os.getpid())])
        except BaseException as e:
            print(f'\033[93m exception in error_handler_function {e}\033[0m')
            pass

    lineno = -1
    fname = 'unknown'
    try:
        try:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            lineno = exc_tb.tb_lineno
        except:
            pass
        print(f'\033[91m Application error in line number: {lineno}, file: {fname} error: {context.error}\033[0m')

    except BaseException as e:
        print("\033[91mException in error_handler_function.\033[0m")
        save_log('pid:' + str(os.getpid()) + ', ' + f'Exception in in error_handler_function: {e}')
        number_of_errors += 1

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    set_text_mode(update)

    query = update.callback_query

    await query.answer()

    query_data_arr = []

    command = query.data

    if '|' in query.data:
        query_data_arr = query.data.split('|')
        command = query_data_arr[0]

    for command_item in commands_arr:
        if command == command_item[0]:
            if len(query_data_arr) > 1:
                await command_item[1](update, context, query_data_arr)
            else:
                await command_item[1](update, context)

def sanitize_string(s: str):
    res = s.replace("<br>", "\n")
    return res

async def send_a_text(update: Update, context: ContextTypes.DEFAULT_TYPE, command_arr: list = None) -> None:
    text_command = ''
    if command_arr and len(command_arr) > 1:
        text_command = command_arr[1]
    elif update.message and update.message.text:
        text_command = update.message.text[1:]
    
    if len(text_command):
        menu = None
        if ('buttons' in languages_arr['_send_text_on_command_' + text_command] and languages_arr['_send_text_on_command_' + text_command]['buttons'][channel_language]):
            menu = []
            for menu_item in languages_arr['_send_text_on_command_' + text_command]["buttons"][channel_language]:
                menu.append([InlineKeyboardButton(menu_item["caption"], callback_data=menu_item["command"] + "|" + menu_item["command"],)])
            menu = InlineKeyboardMarkup(menu)
                
        if ('text_mode' in languages_arr['_send_text_on_command_' + text_command] and len(languages_arr['_send_text_on_command_' + text_command]['text_mode'])):
            set_text_mode(update, languages_arr['_send_text_on_command_' + text_command]['text_mode'])

        await update.effective_message.reply_text(
            languages_arr['_send_text_on_command_' + text_command][channel_language],
            parse_mode='HTML', 
            disable_notification=True,
            disable_web_page_preview=True,
            reply_markup=menu
        )

async def get_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE, command_arr: list = None) -> None:
    keyboard = [[KeyboardButton(text="Share my contact", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard)
    
    await update.effective_message.reply_text(languages_arr['get_phone_number'][channel_language], reply_markup=reply_markup)

commands_arr = [
    ['start', start],
    ['help', help_command],
    ['enter_a_text', enter_a_text],
    ['get_phone_number', get_phone_number],
]

params_file = 'params.json'
try:
    for arg in sys.argv:
        if 'p=' in arg:
            params_file = arg[2:]
except BaseException as e:
    pass

print('params_file:', params_file)

params_arr = json.loads(Path(os.path.dirname(os.path.realpath(__file__)) + '/' + params_file).read_text(encoding="utf8"))

if "debug_mode" in params_arr and params_arr['debug_mode']:
    debug_mode = True

res = get_api_values({
    'custom_command': 'how_many_seconds_ago_app_was_alive',
    'program_name': params_arr['TOKEN'].encode('utf-8').hex(),
})
if not debug_mode and res != None and res != False and len(res) > 0:
    app_was_alive_secs_ago = res['app_was_alive_secs_ago']
    save_log('pid:' + str(os.getpid()) + ', app_was_alive_secs_ago: ' + str(app_was_alive_secs_ago) + ' secs ago')
    if app_was_alive_secs_ago >= 0 and app_was_alive_secs_ago < run_script_after_secs:
        save_log('pid:' + str(os.getpid()) + ', shutdown bot, bot was alive ' + str(app_was_alive_secs_ago) + ' secs ago')
        print(f'\033[93mnot run bot, bot was alive {str(app_was_alive_secs_ago)} secs ago\033[0m')
        sys.exit()
else:
    save_log('pid:' + str(os.getpid()) + ', not received how_many_seconds_ago_app_was_alive')

channel_language = params_arr['channel_language']

languages_arr = json.loads(Path(os.path.dirname(os.path.realpath(__file__)) + '/languages.json').read_text(encoding="utf8"))
for lang_item in languages_arr:
    if '_send_text_on_command_' in lang_item:
        command_name = lang_item[len('_send_text_on_command_'):]
        commands_arr.append([command_name, send_a_text])

# Create the Application and pass it your bot's token.
application = Application.builder().token(params_arr['TOKEN']).build()

# Create command handlers object for commands
for command_item in commands_arr:
    application.add_handler(CommandHandler(command_item[0], command_item[1]))

application.add_handler(CallbackQueryHandler(button))

# Handing Incoming Messages
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler_function))

# Error Handling if any
application.add_error_handler(error_handler_function)

thread = threading.Thread(target=thread_activity, daemon=True, args=(application,))
thread.start()

current_active_loop = asyncio.get_event_loop()

save_log('pid:' + str(os.getpid()) + ', App starting')

print(f'\033[34m bot started \033[0m')
# Run the bot until the user presses Ctrl-C
application.run_polling()


