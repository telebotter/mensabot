import requests
import datetime
import json

def get_url(url):
    response = requests.get(url)
    content = response.content.decode('utf8')
    return content

def get_json_from_url(url):
    content = get_url(url)
    js = json.loads(content)
    return js

def plusdays_date(plusdays):
    '''returns a datetime.datetime object with the date in plusdays days'''
    date=datetime.datetime.now() + datetime.timedelta(days= int(plusdays))
    return date

def datetime_plus_days(date,plusdays):
    '''input a datetime and plus days. output the datetime plus the days'''
    dateplusdays = date + datetime.timedelta(days= int(plusdays))
    return dateplusdays

# not in use
# def timedelta_to_hours(td):
#     '''input a timedelta. output the timedelta in hours'''
#     return td.days*24 + td.seconds//3600

def get_food(date,canteen_1=167,canteen_2=201):
    wanted_date = datetime.datetime.strftime(date, '%Y-%m-%d')
    URL='http://openmensa.org/api/v2/canteens/{}/days/{}/meals'.format(canteen_1, wanted_date)
    URLnw1='http://openmensa.org/api/v2/canteens/{}/days/{}/meals'.format(canteen_2, wanted_date)
    try:
        essen = []
        essen.append(get_json_from_url(URL)[0]['name'])
        essen.append(get_json_from_url(URL)[1]['name'])
        essen.append(get_json_from_url(URL)[2]['name'])
        try:
            essen.append(get_json_from_url(URLnw1)[2]['name'])
        except Exception:
            essen.append('nicht verfügbar')
        mensastatus = True
    except Exception:
        essen = ['nicht verfügbar']*4
        mensastatus = False
    return [essen,mensastatus]

def look_for_fav_food(fav_food):
    '''guckt die nächsten 6 tage nach was es zu essen gibt, wenn das fav_food dabei ist, wird als ausgabe ein timedelta in stunden ausgegeben'''
    td = False
    for ii in range(7):
        date = plusdays_date(ii)
        essens, mensastatus=get_food(date) #durchsuche essen1 innerhalb der nächsten 6 tage nach grünkohl
        essen_1 = essens[0]
        if mensastatus:
            if fav_food.lower() in essen_1.lower():
                today = datetime.datetime.now()
                event_date = datetime_plus_days(today,ii)
                wanted_date = datetime.datetime.strftime(event_date, '%Y-%m-%d')
                twelveoclockthatday = datetime.datetime.strptime(wanted_date, '%Y-%m-%d').replace(hour=12)
                td = twelveoclockthatday - today #stunden bis gk
                return td
                break
    return td

def time_for_alert(td,alarms = [100, 48, 24, 18, 15, 6, 3, 2, 1, 0]):
    '''input one td, output list of td. optional, set list of alarms diffrent #todo(not working jet)'''
    tds = []
    skip_counter = 0
    for xx in alarms:
        minus_td = datetime.timedelta(hours=xx)
        alarm_in = td - minus_td
        if td >= minus_td:# wenn kleiner, dann appenden. sonst nicht
            tds.append(alarm_in)
        else:
            skip_counter += 1
    return [tds, skip_counter]