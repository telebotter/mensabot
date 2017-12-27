import datetime
import datetime as dt
import logging
import configparser

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler, InlineQueryHandler
from emoji import emojize

from models import User
from models import session
from mensa_request import plusdays_date, get_food
from mensa_request import look_for_fav_foods, time_for_alert


class Context:
    """
    Klasse zum speichern statischer Variablen
    """
    commands = ''
    strings = ''  # leere variablen als platzhalter
    strings_alarm = ''
    updater = ''
    # TODO: In config.ini oder strings.ini? besser als hardcode
    alarms = ''
    #hh= 1260
    #alarms = [20+hh, 19+hh, 18+hh, 17+hh, 16+hh, 15+hh, 14+hh, 13+hh, 12+hh,
    # 11+hh]
    admin_id = 0
    s = session
    job_dict = {}
    # job_dict['abo'] = {}  # NOTE: dachte dashier würde dein bug fixen
    # scheinbar wirds wonaders zurück überschrieben


def main():
    """
    Funktion wird beim Programmstart aufgerufen und initialisiert den Bot.
    """

    # SETUP LOGGING
    # TODO: Traceback eventuell in ne extra file? sodass nur error in bot.log
    #  steht und der error mit traceback in error.log? da die sehr lang sein
    # können
    logformat = '%(asctime)s -  %(levelname)s - %(message)s'
    logging.basicConfig(format=logformat,
                        datefmt= '%y-%m-%d %H:%M:%S',
                        level=logging.INFO,
                        #filename='bot.log'
                        )
    logging.info('\n')  # leerzeile zwischen programm neustarts

    # READ CONFIG
    # NOTE ich hab das einlesen verändert, aber nach dem einlesen sollte
    # Context.strings noch genauso wie vorher sein, nur dass die alarme
    # nichtmehr drini sind, die sind jetzt in Context.strings_alarm
    configfile = 'config.ini'
    stringsfile = 'strings.ini'
    privatefile = 'private.ini'
    commandfile = 'commands.ini'
    logging.info('Lese Datei: ' + configfile)
    cfg = configparser.ConfigParser()
    cfg.read(configfile, encoding='UTF8')
    logging.info('Lese Datei: ' + stringsfile)
    strg = configparser.ConfigParser()
    strg.read(stringsfile, encoding='UTF8')
    Context.strings = dict(strg.items('strings'))
    logging.info('Lese Datei: ' + privatefile)
    prvt = configparser.ConfigParser()
    prvt.read(privatefile, encoding='UTF8')
    Context.debug = cfg.getboolean('settings', 'debug', fallback=False)
    token = prvt.get('private', 'token')
    Context.admin_id = int(prvt.get('private', 'admin_id', fallback=0))
    logging.info('Lese Datei: ' + commandfile)
    cmd = configparser.ConfigParser()
    cmd.read(commandfile, encoding='UTF8')
    Context.commands = cmd

    if not Context.debug:
        Context.alarms = [100, 48, 24, 18, 15, 6, 3, 2, 1, 0]
    else:
        #stellt den gk alarm testweise scharf auf die nächsten 10 minuten, dabei wird der alarm getriggert für ein essesn das bei fav_food eingetragen ist und es morgen tatsächlich gibt
        logging.warning('Achtung, Debug ist TRUE')
        hh = datetime.datetime.now().hour -24 # aktuelle uhrzeit, stunden
        mm = datetime.datetime.now().minute  # minuten
        min = (11 -hh)*60+60-mm+1#stunden bis mitternacht plus morgen 12 uhr
        Context.alarms = [min, min - 1, min - 2, min - 3, min - 4, min - 5,
                          min - 6, min - 7, min - 8, min - 9]
        #Context.alarms = [120, 119, 118,117,116,115,114,113,112,111]




    # INIT TELEGRAM BOT
    logging.info('Bot wird initialisiert...')
    updater = Updater(token=token)
    Context.updater = updater
    dispatcher = updater.dispatcher

    # SET HANDLER
    logging.info('Funktionen werden verknüpft...')
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

    admin_echo_all_user_handler = CommandHandler('CrypT1cC0MmanI)!',  # LOL
                                                 admin_echo_all_user)
    dispatcher.add_handler(admin_echo_all_user_handler)
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)
    info_handler = CommandHandler('info', info)
    dispatcher.add_handler(info_handler)
    config_handler = CommandHandler('config', config)
    dispatcher.add_handler(config_handler)

    favfood_alias = Context.commands.get('favfood', 'alias', fallback='favfood')
    favfood_alias = favfood_alias.split(',')
    for alias in favfood_alias:
        dispatcher.add_handler(CommandHandler(alias, favfood, pass_args=True))
    delfav_alias = Context.commands.get(
        'delfavfood', 'alias', fallback='delfavfood').split(',')
    for alias in delfav_alias:
        dispatcher.add_handler(CommandHandler(alias, delfavfood, pass_args=True))

    # OTHER HANDLERS
    dispatcher.add_handler(CallbackQueryHandler(inline_button))
    # Der unknown_handler muss NACH den command handlern stehen
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)


    # READ DB and CREATE JOBS
    logging.info('Datenbank wird ausgelesen...')
    Context.s = session
    logging.info('Userjobs werden erstellt...')
    # abo muss nat. for der forschleife erstellt werden, das war bst. der bug
    Context.job_dict['abo'] = {}
    for usr in Context.s.query(User).all():  # TODO: auslagern in funktion
        # TODO: time
        if usr.abo:
            morgen = 0
            if usr.abo_time.hour >= 14:
                morgen = 1
            usr_abo_job = updater.job_queue.run_daily(abo_food_request,
                                                  usr.abo_time,
                                                  context=[morgen,
                                                           usr.chat_id,
                                                           usr.first_name])
            Context.job_dict['abo'][usr.chat_id] = usr_abo_job


    Context.s.commit()  # TODO: need?
    logging.info('Stündlicher Alarmcheck wird erstellt...')
    job_alarm_check = updater.job_queue.run_repeating(look_for_fav_food_job,
                                                      interval=360, first=0)

    # START TELEGRAM BOT
    updater.start_polling()
    logging.info('Bot läuft!')


# HANDLER FUNCTIONS
def admin_echo_all_user(bot, update):
    """
    Sendet eine Nachricht an alle registrierten User. Der Absender muss in
    admin_id eingetragen sein.

    :param bot: als job automatisch übergegeben
    :param update: als job automatisch übergeben
    """

    if update.message.chat_id == Context.admin_id:
        users = Context.s.query(User).all()
        for usr in users:
            updatetxt = Context.strings['update_txt_1']
            try:
                bot.send_message(chat_id=usr.chat_id, text=updatetxt)
            except Exception as e:
                logging.error(e)
                logging.error('Senden an folgenden User fehlgeschlagen:')
                logging.error(str(usr.chat_id + '; ' + str(usr.first_name)))


def look_for_fav_food_job(bot, job):
    """
    Durchsucht die Lieblingsessen und setzt Alarme für die einzelnen User
    """
    for usr in Context.s.query(User).all():
        fav_foods = usr.fav_food.split(',')  # TODO: development change <- ??
        td, food = look_for_fav_foods(fav_foods)

        if td:
            chatid = usr.chat_id  # TODO: usr wird eh übergeben...
            tds, skip_counter = time_for_alert(td, Context.alarms)
            if not usr.alarm_status:  # NOTE: if not ist schöner als == False
                usr.alarm_status = True
                fav_food_list = []
                alarm_counter = 0
                for time in tds:
                    context = [alarm_counter, skip_counter, chatid, usr, food]
                    alarmjob_tmp = Context.updater.job_queue.run_once(
                        send_alarm, time, context=context)
                    fav_food_list.append(alarmjob_tmp)  # TODO: rename?
                    alarm_counter += 1
                Context.job_dict['fav_foods'] = {usr.chat_id: fav_food_list}


def choose_alarm_text(food):
    """
    Funktion holt sich die passenden Strings zu bestimmten Essen. Wenn das
    Essen nicht eingetragen ist, wird ein Default Text verwendet.
    :param food: <String>
    """
    logging.debug('Versuche Alarmstrings zu Essen zu finden.')
    if food in Context.strings_alarm:
        logging.debug('Spezial Alarm Strings gefunden')
        food_alarm = Context.strings_alarm[food]
    else:
        logging.debug('Keine Alarmstrings.. nehme defaults')
        food_alarm = Context.strings_alarm['default']
    return food_alarm


def send_alarm(bot, job):
    """
    Diese Funktion wird von jedem der Alarmjobs jedes Users aufgerufen und
    sendet den jeweiligen Alarmtext. Die Alarmtexte und der Index werden vom
    Context übergeben.
    """
    # TODO: warum übergibst du ne liste und den index, statt direkt den
    # string zu übergeben? also wenn ichs richtig sehe brauch nur usr + str
    # im context stehen
    texts = choose_alarm_text(job.context[4])
    skip_counter = job.context[1]
    alarm_counter = job.context[0]
    usr = job.context[3]
    chatid = job.context[2]  # todo: wird nicht gebraucht chatid = usr.chat_id
    # TODO: übertrieben lange zeile zerhacken
    message_text = emojize(texts[skip_counter+alarm_counter],
                           use_aliases=True).format(Context.alarms[skip_counter
                                                            + alarm_counter])

    try:
        bot.send_message(chat_id=chatid, text=message_text)
    except Exception as e:
        logging.error(e)
        logging.error('Konnte Alarmtext nicht Senden an:')
        logging.error(str(usr.chat_id) + '; ' + str(usr.first_name))
    if skip_counter+alarm_counter == 9: #10 alarme
        usr.alarm_status = False


def user_stops_abo(bot, update):
    """
    Stoppt den Aboservice für den ausführenden User. Dabei werden bestehende
    Jobs gelöscht, und die user.abo auf false gesetzt.
    """
    c_id = update.message.chat_id
    # returns one or raise E
    usr = Context.s.query(User).filter(User.chat_id == c_id).one()
    msg_txt = emojize(Context.strings['user_stop_abo_text'],
                      use_aliases=True)
    if not usr.abo:  # TODO: muss ggf. userjob trotzdem gelöscht werden?
        bot.send_message(chat_id=usr.chat_id, text=msg_txt)
        return
    usr.abo = False
    try:
        Context.job_dict['abo'][usr.chat_id].schedule_removal()
        del Context.job_dict['abo'][usr.chat_id]
    except Exception as e:
        logging.warning('User versucht abo zu stoppen das nicht existiert')
        logging.warning(usr.chat_id+'; '+usr.first_name)
    bot.send_message(chat_id=update.message.chat_id, text = msg_txt)
    Context.s.commit()
    logging.info('User hat den Aboservice gekündigt')


def user_sets_abo(bot, update, args, job_queue):
    """
    startet den täglichen aboservice. defaultwert ist 9 uhr ct,
    args eingabe mit HHMM
    """
    usr = Context.s.query(User).filter(User.chat_id==update.message.chat_id).one_or_none()
    
    # NOTE: its maybe usefull to escape this with if usr: .. else: create_user

    # TODO: zeitausleselogik in funktion auslagern
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
                logging.warning(e)
                logging.warnning('Konnte die Abozeit nicht aus der Eingabe '
                                 'erkennen')
    try:  # erst löschen, dann neuen job bauen
        Context.job_dict['abo'][usr.chat_id].schedule_removal() #todo
        del Context.job_dict['abo'][usr.chat_id]
    except Exception as e:
        logging.debug(e)
        logging.debug('Konnte für User kein abojob löschen: ')
        logging.debug(str(usr.chat_id) + '; ' + str(usr.first_name))
    morgen = 0
    if usr.abo_time >= datetime.datetime.strptime('1400', '%H%M').time():
        morgen = 1
    Context.job_dict['abo'][usr.chat_id] = job_queue.run_daily(abo_food_request,usr.abo_time,
            context=[morgen,update.message.chat_id,
                update.message.from_user.first_name])
    Context.s.commit()
    msg_txt = emojize(Context.strings['user_set_abo_text'].format(usr.abo_time),
                      use_aliases=True)
    bot.send_message(chat_id=update.message.chat_id, text=msg_txt)
    Context.s.remove()  # todo: useful?


def abo_food_request(bot, job):
    """
    Joah, nimmt das date, holt sich essen über get_food und macht es hübsch.
    Sieht für mich so aus, als könnte das auch direkt in die get_food oder
    ist hierfür ne extra Funktion wegen den Jobs nötig?
    """
    wanted_date = plusdays_date(job.context[0])
    essens, status = get_food(wanted_date)
    if status:
        food_string = make_pretty_string(essens, wanted_date,job.context[2])
        bot.send_message(chat_id=job.context[1], text=food_string)


def user_food_request(bot, update, args):
    """
    Holt das essen für einen bestimmten tag ebenfalls aus der get_food, vgl
    abo_food_request...
    :param args: plusdays
    """
    if len(args) == 0: args = [0]
    try:
        int(args[0])
    except Exception:
        args[0] = 0
    if int(args[0])>7:
        orakel_txt = emojize(Context.strings['orakel'], use_aliases=True)
        bot.send_message(chat_id=update.message.chat_id, text=orakel_txt,
                         parse_mode='Markdown')
        return
    wanted_date = plusdays_date(int(args[0]))
    essens, status = get_food(wanted_date)
    if status:
        food_string = make_pretty_string(essens,
                                         wanted_date,
                                         update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id, text=food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text=emojize(Context.strings['mensa_false'],
                                      use_aliases=True))

# TODO: Die folgenden Funktionen sind alle sogut wie gleich und könnten
# einzeiler sein, wenn man den inhalt in eine Funktion packt. Ist zu
# anstrengend in allen Funktionen immer wieder die gleichen änderungen
# durchzuführen ich spar mir das und wir bauen es iwann um ;)


def heute_request(bot, update):
    """
    Holt sich das essen von heute...
    """
    # NOTE: args == plusdays standdrin war aber n versehen oder?
    wanted_date = plusdays_date(0)
    essens, status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens, wanted_date,
                                        update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id, text=food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text=emojize(Context.strings['mensa_false'],
                                      use_aliases=True))


def morgen_request(bot, update):
    """
    Boah kein bock mehr docstrings zu schreiben...
    """
    wanted_date = plusdays_date(1)
    essens,status=get_food(wanted_date)
    if status:
        food_string= make_pretty_string(essens, wanted_date, update.message.from_user.first_name)
        bot.send_message(chat_id=update.message.chat_id, text= food_string)
    else:
        bot.send_message(chat_id=update.message.chat_id, text=emojize(Context.strings['mensa_false'], use_aliases=True))


def uebermorgen_request(bot, update):
    """
    """
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
        food_string= make_pretty_string(essens, wanted_date,
                                        update.message.from_user.first_name)
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




def start(bot, update):
    msg_text = emojize(Context.strings['start'], use_aliases=True)
    bot.send_message(chat_id=update.message.chat_id,text=msg_text,
                     parse_mode='Markdown')
    chat_id = update.message.chat_id
    # NOTE: ganzen krempel mit der neuen funktion ersetzt
    usr = get_or_create_user(update)


def info(bot, update):
    info_txt = emojize(Context.strings['info'], use_aliases=True)
    bot.send_message(chat_id=update.message.chat_id, text=info_txt,
                     parse_mode='Markdown')


def favfood(bot, update, args):
    """
    /favfood - Handler
    Springt direkt zum food widget aus den settings, wenn keine parameter dran
    sind. Parameter werden direkt an die fav_food liste angehängt.
    """
    usr = get_or_create_user(update)
    logging.debug('User bearbeitet sein Lieblingsessen:')
    logging.debug(str(usr.chat_id) + ', ' + str(usr.first_name))
    if len(args) == 0:
        show_cfg_food(bot, update, usr)
        return
    # argumente an string anhängen.....
    favs = usr.fav_food.split(',')
    for arg in args:
        favs.append(arg)
    usr.fav_food = str.join(',', favs)  # TODO: führende , verhindern
    Context.s.add(usr)  # muss ausgeführt werden, damits geschrieben wird
    Context.s.commit()
    msg_txt = Context.strings['favfood_response'].format(usr.fav_food)
    bot.send_message(text=msg_txt, chat_id=usr.chat_id, parse_mode='Markdown')


def delfavfood(bot, update, args):
    """
    /delfavfood - Handler
    Ohne Argumente öffnet er den Config-Essen-Löschen-Dialog. Ansonsten werden
    die Argumente aus der user.fav_food "liste" gelöscht
    """
    usr = get_or_create_user(update)
    logging.debug('User löscht ein Lieblingsessen:')
    logging.debug(str(usr.chat_id) + ', ' + str(usr.first_name))
    if len(args) == 0:
        show_cfg_food_del(bot, update, usr)
        return
    # argumente aus string löschen..
    for arg in args:
        del_fav_food(usr, arg)  # speichert auch user in db
    msg_txt = Context.strings['delfavfood_response'].format(str(args),
                                                            usr.fav_food)
    bot.send_message(text=msg_txt, chat_id=usr.chat_id, parse_mode='Markdown')


def config(bot, update):
    """
    /config - Handler
    Diese Funktion listet die aktuellen User Einstellungen und bietet einige
    Buttons um diese zu ändern. Noch nicht vorhandene Interaktive Buttons zeigen
    die Hilfetexte zu den Befehlen an.
    Die Buttons sind nicht (wie die Befehle)
    mit Funktionen verknüpft, sondern triggern ein "CallbackQueryEvent"
    um dies aufzufangen verwenden wir einen CallbackQueryHandler.
    Alle Infos die für die "Reaktion" wichtig sind müssen im callback_data
    String verpackt werden.
    """
    try:
        usr = get_or_create_user(update)
    except:
        chat_id = update.callback_query.from_user.id
        usr = Context.s.query(User).filter(User.chat_id==chat_id).one()
        #todo. try except ist in get create eingebaut
    cfg_txt = Context.strings['config'].format(
        str(usr.abo),
        str(usr.abo_time),
        str(usr.fav_food).title(),
        'DE',
        str(usr.mensa_id))
    # NOTE: callbackdata contains: chat_id, widget_id/button_id,
    keyboard = [[
        InlineKeyboardButton('Abo', callback_data='cfg_abo'),
        InlineKeyboardButton('Abozeit', callback_data='cfg_time'),
        InlineKeyboardButton('Essen', callback_data='cfg_food')
        ], [
        InlineKeyboardButton('Sprache', callback_data='cfg_lan'),
        InlineKeyboardButton('Mensa-ID', callback_data='cfg_mensa'),
        InlineKeyboardButton(Context.strings['config_btn_cancel'],
                             callback_data='cfg_cancel')
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    try:  # to get a messg_id
        msg_id = update.callback_query.message.message_id
        bot.edit_message_text(
            text=cfg_txt,
            chat_id=usr.chat_id,
            message_id=msg_id,
            parse_mode='Markdown',
            reply_markup=markup)
    except:  # create new
        bot.send_message(chat_id=usr.chat_id, text=cfg_txt,
                         parse_mode='Markdown', reply_markup=markup)

def inline_button(bot, update):
    """
    Funktion ist mit InlineCallbackHandler verknüpft und wird immer aufgerufen,
    wenn irgendein User in irgendeinem Chat irgendein Button drückt. Daher ist
    sehr darauf zu achten, die updates (usr.id, message.id) sowie die zuordnung
    zu bestimmten buttons (callback_data) jederzeit eindeutig zuordnen zu
    können. Daher am besten update und user objekt direkt weitergeben.
    Der Bot muss immer weitergegeben werden, wenn der Button interaktiv ist.

    Bisherige Buttons:
    * cfg_abo -> show_cfg_abo
    * cfg_time -> show_cfg_time
    """
    data = update.callback_query.data.split(',')
    chat_id = update.callback_query.from_user.id
    usr = Context.s.query(User).filter(User.chat_id == chat_id).one()

    # handle different buttons
    if data[0] == 'cfg_main':
        config(bot, update)
    elif data[0] == 'cfg_cancel':
        cancel_config(bot, update, usr)
    elif data[0] == 'cfg_abo':
        show_cfg_abo(bot, update, usr)
    elif data[0] == 'cfg_time':
        show_cfg_time(bot, update, usr)
    elif data[0] == 'cfg_mensa':
        show_cfg_mensa(bot, update, usr)
    elif data[0] == 'cfg_food':
        show_cfg_food(bot, update, usr)
    elif data[0] == 'cfg_lan':
        show_cfg_lan(bot, update, usr)
    elif data[0] == 'cfg_delfood':
        show_cfg_food_del(bot, update, usr)
    else:
        logging.warning('unbekannter button gedrückt')
        logging.warning(usr.chat_id,usr.first_name)



def unknown(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=emojize(
        Context.strings['user_unknown_command_text'], use_aliases=True))


# OTHER FUNCTIONS
def make_pretty_string(essen_list,date,first_name):
    '''input list of 4 strings; output nice string'''
    date_short = datetime.datetime.strftime(date,'%d.%m')
    # TODO: move strings to strings.ini und diese überlange zeile splitten...
    pretty_string = 'Hallo {}, am {} gibts:\n'.format(first_name,date_short)+ 'Essen 1: ' + essen_list[0] + '\n \n' + 'Essen 2: ' + essen_list[1] + '\n \n' + 'Vegetarisch: ' + essen_list[2] + '\n \n' + 'Zusatzessen NW1: ' + essen_list[3]
    return  pretty_string


def show_cfg_abo(bot, update, usr):
    """
    Ändert die usr.abo wenn daten übergeben werden (vom toggle button)
    Erestzt den Inhalt der zugehörigen Nachricht, durch abotext und buttons.
    :param usr: User-Objekt aus models.py
    """
    # TODO: strings durch ini Einträge ersetzen
    msg_id = update.callback_query.message.message_id
    chat_id = update.callback_query.from_user.id
    data = update.callback_query.data.split(',')
    logging.debug(data)
    if len(data)>1 and data[1] == '0':
        usr.abo = False
    elif len(data)>1 and data[1] == '1':
        usr.abo = True
    status_txt = 'aus'
    toggle_txt = Context.strings['config_btn_on']
    val = ',1'  # autsch das ist dirty
    if usr.abo:
        status_txt = 'an'
        toggle_txt = Context.strings['config_btn_off']
        val = ',0'

    msg_txt = Context.strings['config_abo'].format(status_txt)
    keyboard = [[InlineKeyboardButton(Context.strings['config_btn_back'],
                                      callback_data='cfg_main'),
                 InlineKeyboardButton(toggle_txt, callback_data='cfg_abo'+val),
                 InlineKeyboardButton(Context.strings['config_btn_cancel'],
                                      callback_data='cfg_cancel')
                 ]]
    markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        text=msg_txt,
        chat_id=chat_id,
        message_id=msg_id,
        parse_mode='Markdown',
        reply_markup=markup
    )

def show_cfg_time(bot, update, usr):
    """
    Erestzt den Inhalt der zugehörigen Nachricht, durch abotime und buttons.
    :param usr: User-Objekt aus models.py
    """
    msg_id = update.callback_query.message.message_id
    chat_id = update.callback_query.from_user.id
    msg_txt = Context.strings['config_abo_time'].format(str(usr.abo_time))
    keyboard = [[InlineKeyboardButton(Context.strings['config_btn_back'],
                                      callback_data='cfg_main'),
                 InlineKeyboardButton(Context.strings['config_btn_cancel'],
                                      callback_data='cfg_cancel')
                 ]]
    markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        text=msg_txt,
        chat_id=chat_id,
        message_id=msg_id,
        parse_mode='Markdown',
        reply_markup=markup
    )


def show_cfg_mensa(bot, update, usr):
    """
    Ersetzt den Inhalt des Config-Dialogs mit der Mensa Seite. Zurzeit steht
    dort nur ein Hinweis, dass dieser Service noch in Arbeit ist.
    :param usr: User-Object aus models.py
    """
    msg_id = update.callback_query.message.message_id
    chat_id = update.callback_query.from_user.id
    msg_txt = Context.strings['config_mensa'].format(str(usr.mensa_id))
    keyboard = [[InlineKeyboardButton(Context.strings['config_btn_back'],
                                      callback_data='cfg_main'),
                 InlineKeyboardButton(Context.strings['config_btn_cancel'],
                                      callback_data='cfg_cancel')
                 ]]
    markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        text=msg_txt,
        chat_id=chat_id,
        message_id=msg_id,
        parse_mode='Markdown',
        reply_markup=markup)


def show_cfg_food(bot, update, usr):
    """
    Ersetzt den Inhalt des Config-Dialogs mit der Lieblingsessen Seite.
    Zurzeit steht dort nur ein Hinweis, dass dieser Service noch in Arbeit ist.
    :param usr: User-Object aus models.py
    """
    fav_food = str.join(', ', usr.fav_food.split(',')).title()
    msg_txt = Context.strings['config_food'].format(str(fav_food))
    keyboard = [[InlineKeyboardButton(Context.strings['config_btn_back'],
                                      callback_data='cfg_main'),
                 InlineKeyboardButton(Context.strings['config_btn_delfood'],
                                      callback_data='cfg_delfood'),
                 InlineKeyboardButton(Context.strings['config_btn_cancel'],
                                      callback_data='cfg_cancel')
                 ]]

    markup = InlineKeyboardMarkup(keyboard)
    try:  # to find related message
        msg_id = update.callback_query.message.message_id
        bot.edit_message_text(
            text=msg_txt,
            chat_id=usr.chat_id,
            message_id=msg_id,
            parse_mode='Markdown',
            reply_markup=markup)
    except:  # create new message
        logging.info('cfg_food Dialog aufgerufen ohne message_id')
        bot.send_message(
            chat_id=usr.chat_id,
            text=msg_txt,
            parse_mode='Markdown',
            reply_markup=markup)


def show_cfg_food_del(bot, update, usr):
    """
    Zeigt eine Buttonliste im Config-Dialog. Die Buttons entsprechen den
    eingetragenen Essen. Um ein essen zu löschen wird der string als data[1]
    übergeben und dann vom button handler an die delete funktion übergeben.
    """
    data = update.callback_query.data.split(',')
    if len(data) > 1:
        del_fav_food(usr, data[1])

    msg_txt = Context.strings['config_food_del']
    keyboard = []
    for fav in usr.fav_food.split(','):
        keyboard.append([InlineKeyboardButton(
            fav, callback_data='cfg_delfood,'+fav)])
    markup = InlineKeyboardMarkup(keyboard)
    try:  # to find related message
        msg_id = update.callback_query.message.message_id
        bot.edit_message_text(
            text=msg_txt,
            chat_id=usr.chat_id,
            message_id=msg_id,
            parse_mode='Markdown',
            reply_markup=markup)
    except:  # create new message
        logging.debug('cfg_food_del Dialog aufgerufen ohne message_id')
        bot.send_message(
            chat_id=usr.chat_id,
            text=msg_txt,
            parse_mode='Markdown',
            reply_markup=markup)




def show_cfg_lan(bot, update, usr):
    """
        Ersetzt den Inhalt des Config-Dialogs mit den Spracheinstellungen.
        Zurzeit steht dort nur ein Hinweis, dass dieser Service in Arbeit ist.
        :param usr: User-Object aus models.py
        """
    msg_id = update.callback_query.message.message_id
    chat_id = update.callback_query.from_user.id
    fav_food = str.join(', ', usr.fav_food.split(',')).title()
    msg_txt = Context.strings['config_lan']
    keyboard = [[InlineKeyboardButton(Context.strings['config_btn_back'],
                                      callback_data='cfg_main'),
                 InlineKeyboardButton(Context.strings['config_btn_cancel'],
                                      callback_data='cfg_cancel')
                 ]]
    markup = InlineKeyboardMarkup(keyboard)
    bot.edit_message_text(
        text=msg_txt,
        chat_id=chat_id,
        message_id=msg_id,
        parse_mode='Markdown',
        reply_markup=markup)


def cancel_config(bot, update, usr):
    """
    Schließt den Config-Dialog, also löscht die Nachricht von der aus der
    Button gedrückt wurde.
    """
    msg_id = update.callback_query.message.message_id
    chat_id = update.callback_query.from_user.id
    logging.debug('User schließt Settings')
    bot.delete_message(
        chat_id=chat_id,
        message_id=msg_id,
    )


def get_or_create_user(update):
    """
    Diese Funktion durchsucht die Datenbank nach einem user mit passender
    chat_id, wenn keiner gefunden wurde, wird ein neuer erstellt in die DB
    geschrieben und übergeben.
    :param update: Nimmt ein telegram update objekt (für id und name)
    :return user: User-Objekt das aus der Datenbank erstellt wurde
    """
    try:
        chat_id = update.message.chat_id
    except:
        chat_id = update.callback_query.from_user.id
    usr = Context.s.query(User).filter(User.chat_id==chat_id).one_or_none()
    if not usr:
        try:
            # CREATE NEW USER
            usr = User()
            usr.chat_id = chat_id
            # TODO: check obs auch mit inline button geht...
            usr.first_name = update.message.from_user.first_name

            Context.s.add(usr)  # add object
            Context.s.commit()  # save changes
            logging.info('Neuen User registriert:')
            logging.info(str(usr.chat_id) + '; ' + str(usr.first_name))
            # NOTE: Bin mir nicht sicher, ob es einen unterschiedmacht den User
            # aus der DB zu lesen oder direkt zu erstellen, zur sicherheit einmal
            # neu einlesen. Außerdem verursacht das auch nen fehler wenn das
            # erstellen nicht geklappt hat (was gewollt ist)
            usr = Context.s.query(User).filter(User.chat_id == chat_id).one()
        except Exception as e:
            logging.error('User hat versucht weiter mit den Buttons zu '
                          'arbeiten obwohl er nicht in db ist:')
            logging.error(usr.chat_id,usr.first_name)
    return usr


def del_fav_food(usr, food):
    """
    Removes matching food string from the "list" usr.fav_food.
    :param usr: User-Object from models.py
    :param food: String of food to be removed from list
    """
    favs = usr.fav_food.split(',')
    new_favs = [x for x in favs if food not in x]
    new_favs = str.join(',', new_favs)
    usr.fav_food = new_favs
    Context.s.add(usr)
    Context.s.commit()


# TODO: '\U0001F92F \U00002639 \U0001F9D1\U0001F3FD'
# ...sowas in die gkconfig.ini reinballern!
# TODO: funktionen sortieren und ggf. einige auslagern zB alle
# handler-functionen in ne functions.py (dafür müssen wir aber erst diese
# nervige Context klasse loswerden ;) )

main()
