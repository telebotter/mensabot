from user_class import User
from dbhelper import DBHelper
from mensa_request import plusdays_date,get_food,look_for_fav_food,time_for_alert
import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from emoji import emojize
import logging
import configparser

class Context():
    '''klasse für die statische variable'''
    usr_dict = 'user dictionary'
    strings = 'irgendwas'

def main():
    cfg = configparser.ConfigParser()
    cfg.read('gkconfig.ini', encoding='UTF8')
    Context.strings = dict(cfg.items('strings'))
    # following lines could just be: private_token = 'your-token'
    prvt = configparser.ConfigParser()
    prvt.read('private.ini',encoding='UTF8')
    private_token = prvt.get('private', 'testtoken')

    updater = Updater(token=private_token)
    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    stop_abo_handler = CommandHandler('stopabo', user_stops_abo)
    dispatcher.add_handler(stop_abo_handler)
    set_abo_handler = CommandHandler('abo', user_sets_abo, pass_args=True, pass_job_queue=True)
    dispatcher.add_handler(set_abo_handler)

    user_food_request_handler = CommandHandler('essen', user_food_request, pass_args=True)
    dispatcher.add_handler(user_food_request_handler)
    heute_request_handler = CommandHandler('heute', heute_request)
    dispatcher.add_handler(heute_request_handler)
    morgen_request_handler = CommandHandler('morgen', morgen_request)
    dispatcher.add_handler(morgen_request_handler)
    uebermorgen_request_handler = CommandHandler('übermorgen', uebermorgen_request)
    dispatcher.add_handler(uebermorgen_request_handler)
    ueber2morgen_request_handler = CommandHandler('überübermorgen', ueber2morgen_request)
    dispatcher.add_handler(ueber2morgen_request_handler)
    ueber3morgen_request_handler = CommandHandler('überüberübermorgen', ueber3morgen_request)
    dispatcher.add_handler(ueber3morgen_request_handler)

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    info_handler = CommandHandler('info', info)
    dispatcher.add_handler(info_handler)
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    usr_dict = init_users_from_db(updater)
    Context.usr_dict = usr_dict

    updater.start_polling()

def init_users_from_db(updater):
    '''ließt zum programmstart die db ein und erstellt ein dictionary mit allen usern, wo die ganzen einträge drinne stehen'''
    db = DBHelper()
    user_dict = {}
    for i in db.get_items():
        usr = User(i[1])
        usr.first_name = i[0]
        usr.fav_food = i[2]
        usr.abo = i[3]
        usr.abo_time = i[4]
        if usr.abo == '1':
            usr.job_abo = updater.job_queue.run_daily(listme, usr.get_abo_time())
        user_dict[usr.chat_id]=usr
    return user_dict

def user_stops_abo(bot,update):
    '''stoppet den täglichen aboservice'''
    db = DBHelper()
    usr = Context.usr_dict[str(update.message.chat_id)]
    db.change_entry(usr, 'abo', '0')
    if not usr.job_abo:
        bot.send_message(chat_id=update.message.chat_id,text =  emojize(Context.strings['user_stop_abo_text'],use_aliases=True))
        return
    usr.job_abo.schedule_removal()
    usr.job_abo = None
    bot.send_message(chat_id=update.message.chat_id,text = emojize(Context.strings['user_stop_abo_text'],use_aliases=True))

def user_sets_abo(bot,update,args,job_queue):
    '''startet den täglichen aboservice. defaultwert ist 9 uhr ct, args eingabe mit HHMM'''
    db = DBHelper()
    usr = Context.usr_dict[str(update.message.chat_id)]
    if len(args) < 1: args.append(usr.abo_time)
    db.change_entry(usr, 'abo', '1')
    usr.abo = '1'
    usr.abo_time = args[0]
    try:
        usr_time = usr.get_abo_time()
    except Exception:
        usr.abo_time = '0915'
        args[0] = '0915'
        usr_time = usr.get_abo_time()
    db.change_entry(usr, 'abo_time', args[0])
    today_or_tomorrow = 0
    if usr_time > datetime.datetime.strptime('14', '%H%M').time(): today_or_tomorrow = 1
    job_queue.run_daily(abo_food_request,usr_time,context=[today_or_tomorrow,update.message.chat_id,update.message.from_user.first_name])
    bot.send_message(chat_id=update.message.chat_id,text = emojize(Context.strings['user_set_abo_text'].format(usr_time),use_aliases=True))

def abo_food_request(bot,job):
    wanted_date = plusdays_date(job.context[0])
    essens, status = get_food(wanted_date)
    if status:
        food_string = make_pretty_string(essens, wanted_date,job.context[2])
        bot.send_message(chat_id=job.context[1], text=food_string)

def user_food_request(bot, update, args):
    '''args == plusdays'''
    if len(args) == 0: args = [0]
    try:
        int(args[0])
    except Exception:
        args[0] = 0
    if int(args[0])>7:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['orakel'], use_aliases=True),parse_mode='Markdown')
        return
    wanted_date = plusdays_date(int(args[0]))
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens,wanted_date,update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id,text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))

def heute_request(bot, update):
    '''args == plusdays'''
    wanted_date = plusdays_date(0)
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens,wanted_date,update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id,text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))

def morgen_request(bot, update):
    '''args == plusdays'''
    wanted_date = plusdays_date(1)
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens,wanted_date,update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id,text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))

def uebermorgen_request(bot, update):
    '''args == plusdays'''
    wanted_date = plusdays_date(2)
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens,wanted_date,update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id,text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))

def ueber2morgen_request(bot, update):
    '''args == plusdays'''
    wanted_date = plusdays_date(3)
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens,wanted_date,update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id,text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))

def ueber3morgen_request(bot, update):
    '''args == plusdays'''
    wanted_date = plusdays_date(4)
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens,wanted_date,update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id,text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))

def make_pretty_string(essen_list,date,first_name):
    '''input list of 4 strings; output nice string'''
    date_short = datetime.datetime.strftime(date,'%d.%m')
    pretty_string = 'Hallo {}, am {} gibts:\n'.format(first_name,date_short)+ 'Essen 1: ' + essen_list[0] + '\n \n' + 'Essen 2: ' + essen_list[1] + '\n \n' + 'Vegetarisch: ' + essen_list[2] + '\n \n' + 'Zusatzessen NW1: ' + essen_list[3]
    return  pretty_string

def start(bot,update):
    bot.send_message(chat_id=update.message.chat_id,text=emojize(Context.strings['start'], use_aliases=True),parse_mode='Markdown')
    chat_id = str(update.message.chat_id)
    if not chat_id in Context.usr_dict:
        usr = User(chat_id)
        usr.first_name = update.message.from_user.first_name
        Context.usr_dict[chat_id] = usr
        usr.add()

def info(bot,update):
    bot.send_message(chat_id=update.message.chat_id,text=emojize(Context.strings['info'], use_aliases=True),parse_mode='Markdown')

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['user_unknown_command_text'],use_aliases=True))

def listme(bot, job):
    '''test job, sendet hendrik eine nachricht'''
    bot.send_message(chat_id=129116350, text='blab')

main()
