from mensa_request import plusdays_date,get_food,look_for_fav_food,time_for_alert
import datetime

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from emoji import emojize
import logging
import configparser


# NOTE: added imports
from models import User
from models import session
# Hendrik insert line
# NOTE: removed imports
#from user_class import User
#from dbhelper import DBHelper




class Context():
    '''klasse für die statische variable'''
    # NOTE: not longer needed
    #usr_dict = 'user dictionary'
    strings = 'irgendwas'
    updater = 'was anderes'
    alarms = [100, 48, 24, 18, 15, 6, 3, 2, 1, 0]
    #alarms = [55, 50, 45, 44, 43, 42, 41, 40, 35, 34]
    admin_id = 0
    s = session

def main():
    cfg = configparser.ConfigParser()
    cfg.read('gkconfig.ini', encoding='UTF8')
    Context.strings = dict(cfg.items('strings'))
    # following lines could just be: private_token = 'your-token'
    prvt = configparser.ConfigParser()
    prvt.read('private.ini',encoding='UTF8')
    private_token = prvt.get('private', 'realtoken')
    Context.admin_id = int(prvt.get('private', 'admin_id'))

    updater = Updater(token=private_token)
    Context.updater = updater
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

    admin_echo_all_user_handler = CommandHandler('CrypT1cC0MmanI)!', admin_echo_all_user)
    dispatcher.add_handler(admin_echo_all_user_handler)
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    info_handler = CommandHandler('info', info)
    dispatcher.add_handler(info_handler)
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # NOTE: replaced
    #usr_dict = init_users_from_db(updater)
    #Context.usr_dict = usr_dict

    job_jede_stunde_gucken = updater.job_queue.run_repeating(look_for_fav_food_job, interval=360, first=0)
    updater.start_polling()

def admin_echo_all_user(bot,update):
    if update.message.chat_id == Context.admin_id:
        # NOTE: No need for this
        #usr_dict = Context.usr_dict
        # just do:
        users = Context.s.query(User).all()
        # NOTE: loop will be easier
        #for id in usr_dict:
        for usr in users:
            #usr = usr_dict[id]
            updatetxt = Context.strings['update_txt_1']
            try:
                # NOTE: chat_id is not key but user property
                #bot.send_message(chat_id= int(id), text= updatetxt)
                bot.send_message(chat_id=usr.chat_id, text=updatetxt)
            except Exception as e:
                print(e)  # TODO: use logging.error instead of print


def look_for_fav_food_job(bot,job):
    '''looking for fav_food, setting new alarms if nessesary. For each user'''
    # EDIT: 
    #usr_dict = Context.usr_dict
    #for yy in usr_dict:
    for usr in Context.s.query(User).all():
        #usr = usr_dict[yy]
        fav_food = usr.fav_food
        food_counter = 0 #0 = fav_food, 1 = weihnachtsessen
        special_alarm = 'Weihnachtsessen'
        if look_for_fav_food(special_alarm):
            td = look_for_fav_food(special_alarm)
            food_counter = 1
        else:
            td = look_for_fav_food(fav_food)
        if td:
            chatid = usr.chat_id
            tds, skip_counter = time_for_alert(td,Context.alarms)
            if usr.alarm_status == False:
                usr.alarm_status = True
                alarm_counter = 0
                for time in tds:
                    usr.job_fav_food_list = []
                    usr.job_fav_food_list.append(Context.updater.job_queue.run_once(send_alarm, time,context=[alarm_counter,skip_counter,chatid,usr,food_counter]))
                    alarm_counter += 1

def send_alarm(bot,job):
    texts = Context.strings['alarm_text'].split('\n')
    skip_counter = job.context[1]
    alarm_counter = job.context[0]
    usr = job.context[3]  # TODO: is this a passed User-Model-Object?
    chatid = job.context[2]  # TODO: if yes why the other context? its all in usr
    food_counter = job.context[4]
    if food_counter == 0:
        message_text = emojize(texts[skip_counter+alarm_counter],use_aliases=True).format(Context.alarms[skip_counter+alarm_counter])
    elif food_counter == 1:
        texts = Context.strings['xmas_alarm_text'].split('\n')
        message_text = emojize(texts[skip_counter+alarm_counter],use_aliases=True).format(Context.alarms[skip_counter+alarm_counter])
    try:
        bot.send_message(chat_id=chatid ,text=message_text )
    except Exception as e:
        print(e)
    if skip_counter+alarm_counter == 9: #10 alarme
        usr.alarm_status = False
    a = datetime.datetime.now()
    print(a)



# NOTE: this is not longer needed
"""
def init_users_from_db(updater):
    db = DBHelper()
    user_dict = {}
    for i in db.get_items():
        usr = User(i[1])
        usr.first_name = i[0]
        usr.fav_food = i[2]
        usr.abo = i[3]
        usr.abo_time = i[4]
        if usr.abo == '1':
            today_or_tomorrow = 0
            if usr.get_abo_time() > datetime.datetime.strptime('1400', '%H%M').time():
                today_or_tomorrow = 1
            usr.job_abo = updater.job_queue.run_daily(abo_food_request, usr.get_abo_time(),context=[today_or_tomorrow,usr.chat_id,usr.first_name])
        user_dict[usr.chat_id]=usr
    return user_dict
"""


def user_stops_abo(bot,update):
    '''stoppet den täglichen aboservice'''
    # NOTE: this db is not longer needed
    #db = DBHelper()
    #usr = Context.usr_dict[str(update.message.chat_id)]
    #db.change_entry(usr, 'abo', '0')
    c_id = update.message.chat_id
    usr = Context.s.query(User).filter(chat_id == c_id).one()  # returns one or raise E
    if not usr.job_abo:
        bot.send_message(chat_id=usr.chat_id, 
                text=emojize(Context.strings['user_stop_abo_text'], use_aliases=True))
        return
    usr.job_abo.schedule_removal()
    usr.job_abo = None
    bot.send_message(chat_id=update.message.chat_id,text = emojize(Context.strings['user_stop_abo_text'],use_aliases=True))

def user_sets_abo(bot,update,args,job_queue):
    '''startet den täglichen aboservice. defaultwert ist 9 uhr ct, args eingabe mit HHMM'''
    # NOTE: remove another dbHelper
    #db = DBHelper()
    #usr = Context.usr_dict[str(update.message.chat_id)]
    usr = Context.s.query(User).filter(chat_id==update.message.chat_id).one_or_none()
    # NOTE: its maybe usefull to escape this with if usr: .. else: create_user

    if len(args) < 1: args.append(usr.abo_time)  #This is smart :)
    # NOTE: This was ugly ;) sry
    #db.change_entry(usr, 'abo', '1')
    #usr.abo = '1'
    #usr.abo_time = args[0]
    usr.abo = True
    try:
        usr.abo_time = dt.time(args[0])
    except:
        pass

    try: #erst löschen, dann neuen job bauen
        usr.job_abo.schedule_removal()
        usr.job_abo = None
    except Exception as e:
        print(e)
    # NOTE: this block is not needed anylonger, user_time is also not needed
    """
    try:
        # NOTE: get_abo_time not needed abo_time is time-obj
        usr_time = usr.get_abo_time()
    except Exception:
        usr.abo_time = '0915'
        args[0] = '0915'
        usr_time = usr.get_abo_time()
    """
    # NOTE: this is done by default now
    #db.change_entry(usr, 'abo_time', args[0])

    today_or_tomorrow = 0
    if usr.abo_time > datetime.datetime.strptime('1400', '%H%M').time():
        today_or_tomorrow = 1
    #NOTE: replaced usr_time with usr.abo_time
    usr.job_abo = job_queue.run_daily(abo_food_request,usr.abo_time,
            context=[today_or_tomorrow,update.message.chat_id,
                update.message.from_user.first_name])
    #NOTE: all above db.change stuff can be done with:
    Context.s.commit()
    bot.send_message(chat_id=update.message.chat_id,text = emojize(Context.strings['user_set_abo_text'].format(usr.abo_time),use_aliases=True))

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
    # NOTE: removed the string (can be int now)
    #chat_id = str(update.message.chat_id)
    chat_id = update.message.chat_id
    #if not chat_id in Context.usr_dict:
    if not Context.s.query(User).filter(User.chat_id==chat_id).one_or_none():
        # NOTE:
        #usr = User(chat_id)
        usr = User()
        usr.chat_id = chat_id
        usr.first_name = update.message.from_user.first_name
        # NOTE: user stuff bleibt aber das adden geht jetzt leicht anders
        #Context.usr_dict[chat_id] = usr
        #usr.add()
        Context.s.add(usr)  # add object
        Context.s.commit()  # save changes

def info(bot,update):
    bot.send_message(chat_id=update.message.chat_id,text=emojize(Context.strings['info'], use_aliases=True),parse_mode='Markdown')

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['user_unknown_command_text'],use_aliases=True))

def listme(bot, job):
    '''test job, sendet hendrik eine nachricht'''
    bot.send_message(chat_id=129116350, text='blab')


main()
