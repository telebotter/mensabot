from mensa_request import plusdays_date,get_food,look_for_fav_foods,time_for_alert
import datetime
import datetime as dt

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from emoji import emojize
import logging
import configparser

from models import User
from models import session





class Context():
    '''klasse für die statische variable'''
    debug = None
    alarms = [100, 48, 24, 18, 15, 6, 3, 2, 1, 0]
    strings = 'irgendwas'
    updater = 'was anderes'
    admin_id = 0
    s = session
    job_dict = {}

def main():
    cfg = configparser.ConfigParser()
    cfg.read('gkconfig.ini', encoding='UTF8')
    Context.strings = dict(cfg.items('strings'))
    Context.debug = cfg.getboolean('settings','debug',fallback=False)

    if not Context.debug:
        Context.alarms = [100, 48, 24, 18, 15, 6, 3, 2, 1, 0]
    else:
        print('Achtung, Debug ist auf TRUE geschaltet')
        hh = datetime.datetime.now().hour -24 # aktuelle uhrzeit, stunden
        mm = datetime.datetime.now().minute  # minuten
        min = (11 -hh)*60+60-mm+1#stunden bis mitternacht plus morgen 12 uhr
        Context.alarms = [min, min - 1, min - 2, min - 3, min - 4, min - 5, min - 6, min - 7, min - 8, min - 9]
        #Context.alarms = [120, 119, 118,117,116,115,114,113,112,111]

    # following lines could just be: private_token = 'your-token'
    prvt = configparser.ConfigParser()
    prvt.read('private.ini',encoding='UTF8')
    private_token = prvt.get('private', 'token')
    Context.admin_id = int(prvt.get('private', 'admin_id'))

    updater = Updater(token=private_token)
    Context.updater = updater
    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s '
                               '- %(message)s', level=logging.INFO)

    stop_abo_handler = CommandHandler('stopabo', user_stops_abo)
    dispatcher.add_handler(stop_abo_handler)
    set_abo_handler = CommandHandler('abo', user_sets_abo, pass_args=True,
                                     pass_job_queue=True)
    dispatcher.add_handler(set_abo_handler)

    user_food_request_handler = CommandHandler('essen', user_food_request,
                                               pass_args=True)
    dispatcher.add_handler(user_food_request_handler)
    heute_request_handler = CommandHandler('heute', heute_request)
    dispatcher.add_handler(heute_request_handler)
    morgen_request_handler = CommandHandler('morgen', morgen_request)
    dispatcher.add_handler(morgen_request_handler)
    uebermorgen_request_handler = CommandHandler('übermorgen',
                                                 uebermorgen_request)
    dispatcher.add_handler(uebermorgen_request_handler)
    ueber2morgen_request_handler = CommandHandler('überübermorgen',
                                                  ueber2morgen_request)
    dispatcher.add_handler(ueber2morgen_request_handler)
    ueber3morgen_request_handler = CommandHandler('überüberübermorgen',
                                                  ueber3morgen_request)
    dispatcher.add_handler(ueber3morgen_request_handler)

    admin_echo_all_user_handler = CommandHandler('CrypT1cC0MmanI)!',
                                                 admin_echo_all_user)
    dispatcher.add_handler(admin_echo_all_user_handler)
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    info_handler = CommandHandler('info', info)
    dispatcher.add_handler(info_handler)
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)
    Context.s = session

    Context.job_dict['abo'] = {}
    for usr in Context.s.query(User).all(): #todo auslagern in funktion
        #TODO: time 
        if usr.abo:
            morgen = 0
            if usr.abo_time.hour >= 14:
                morgen = 1
            usr_job = updater.job_queue.run_daily(abo_food_request, usr.abo_time,
                                                  context=[morgen,
                                                           usr.chat_id,
                                                           usr.first_name])

            Context.job_dict['abo'][usr.chat_id] = usr_job


    Context.s.commit()
    job_jede_stunde_gucken = updater.job_queue.run_repeating(look_for_fav_food_job,
                                                             interval=360, first=0)
    updater.start_polling()

def admin_echo_all_user(bot,update):
    if update.message.chat_id == Context.admin_id:
        users = Context.s.query(User).all()
        # NOTE: loop will be easier
        #for id in usr_dict:
        for usr in users:
            updatetxt = Context.strings['update_txt_1']
            try:
                bot.send_message(chat_id=usr.chat_id, text=updatetxt)
            except Exception as e:
                print(e)  # TODO: use logging.error instead of print


def look_for_fav_food_job(bot,job):
    '''looking for fav_food, setting new alarms if nessesary. For each user'''
    for usr in Context.s.query(User).all():
        fav_foods = usr.fav_food.split(',') #todo development change
        td,food = look_for_fav_foods(fav_foods)

        if td:
            chatid = usr.chat_id
            tds, skip_counter = time_for_alert(td,Context.alarms,Context.debug)
            if usr.alarm_status == False:
                usr.alarm_status = True
                fav_food_list = []
                alarm_counter = 0
                for time in tds:
                    context = [alarm_counter,skip_counter,chatid,usr,food]
                    alarmjob_tmp = Context.updater.job_queue.run_once(send_alarm,
                                                        time,context=context)
                    fav_food_list.append(alarmjob_tmp)
                    alarm_counter += 1
                Context.job_dict['fav_foods'] = {usr.chat_id:fav_food_list}

def choose_alarm_text(food):
    '''input fav_food string, returns a list of alarmstrings'''
    xmas = Context.strings['xmas_alarm_text'].split('\n')
    gk = Context.strings['alarm_text'].split('\n')
    default = Context.strings['default_alarm_text'].split('\n')
    alarm_dict = {'weihnachtsessen':xmas,
                  'grünkohl':gk,
                  'default':default}
    if food in alarm_dict:
        return alarm_dict[food]
    else:
        return alarm_dict['default']


def send_alarm(bot,job):
    food = job.context[4]
    texts = choose_alarm_text(food)
    skip_counter = job.context[1]
    alarm_counter = job.context[0]
    usr = job.context[3]
    chatid = job.context[2]
    message_text = emojize(texts[skip_counter+alarm_counter],use_aliases=True).format(Context.alarms[skip_counter+alarm_counter],food.title())#.title macht ersten buchstagen zu uppercase
    try:
        bot.send_message(chat_id=chatid ,text=message_text)
    except Exception as e:
        print(e)
    if skip_counter+alarm_counter == 9: #10 alarme
        usr.alarm_status = False
    a = datetime.datetime.now()
    print(a)


def user_stops_abo(bot,update):
    '''stoppet den täglichen aboservice'''
    c_id = update.message.chat_id
    usr = Context.s.query(User).filter(User.chat_id == c_id).one()  # returns one or raise E
    if not usr.abo:
        bot.send_message(chat_id=usr.chat_id, 
                text=emojize(Context.strings['user_stop_abo_text'], use_aliases=True))
        return
    usr.abo = False
    Context.job_dict['abo'][usr.chat_id].schedule_removal()
    del Context.job_dict['abo'][usr.chat_id]
    bot.send_message(chat_id=update.message.chat_id,text = emojize(Context.strings['user_stop_abo_text'],use_aliases=True))
    Context.s.commit()

def user_sets_abo(bot,update,args,job_queue):
    '''startet den täglichen aboservice. defaultwert ist 9 uhr ct, args eingabe mit HHMM'''
    usr = Context.s.query(User).filter(User.chat_id==update.message.chat_id).one_or_none()
    # NOTE: its maybe usefull to escape this with if usr: .. else: create_user

    #todo: zeitausleselogik in funktion auslagern
    usr.abo = True
    if len(args) >= 2:
        try:
            usr.abo_time = dt.datetime.strptime(args[0]+args[1], '%H%M').time()
        except Exception as e:
            print(e)
    elif len(args) > 0:
        try:
            usr.abo_time = dt.datetime.strptime(args[0], '%H%M').time()
        except Exception as er:
            try: 
                usr.abo_time = dt.datetime.strptime(args[0], '%H:%M').time()
            except Exception as e:
                print(e)  # todo: log

    try: #erst löschen, dann neuen job bauen
        Context.job_dict['abo'][usr.chat_id].schedule_removal() #todo
        del Context.job_dict['abo'][usr.chat_id]
    except Exception as e:
        print(e)
    morgen = 0
    if usr.abo_time >= datetime.datetime.strptime('1400', '%H%M').time():
        morgen = 1
    Context.job_dict['abo'][usr.chat_id] = job_queue.run_daily(abo_food_request,usr.abo_time,
            context=[morgen,update.message.chat_id,
                update.message.from_user.first_name])
    Context.s.commit()
    bot.send_message(chat_id=update.message.chat_id,text = emojize(Context.strings['user_set_abo_text'].format(usr.abo_time),use_aliases=True))
    Context.s.remove()  # todo: useful?

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
        bot.send_message(chat_id=update.message.chat_id,text=food_string)
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
    chat_id = update.message.chat_id
    #if not chat_id in Context.usr_dict:
    if not Context.s.query(User).filter(User.chat_id==chat_id).one_or_none():
        usr = User()
        usr.chat_id = chat_id
        usr.first_name = update.message.from_user.first_name
        Context.s.add(usr)  # add object
        Context.s.commit()  # save changes
        #todo create user funktion

def info(bot,update):
    bot.send_message(chat_id=update.message.chat_id,text=emojize(Context.strings['info'], use_aliases=True),parse_mode='Markdown')

def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['user_unknown_command_text'],use_aliases=True))

##todo##'\U0001F92F \U00002639 \U0001F9D1\U0001F3FD' ...sowas in die gkconfig.ini reinballern!


main()
