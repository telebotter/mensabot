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
        #text='Essen 1: ' + essen[0] + '\n \n' + 'Essen 2: ' + essen[1] + '\n \n' + 'Vegetarisch: ' + essen[2] + '\n \n' + 'Zusatzessen NW1: ' + essen[3]
        mensastatus = True
    except Exception:
        #text = 'Heute ist die Mensa geschlossen. Ich habe keine Informationen über das Essen.'
        essen = ['nicht verfügbar']*4
        mensastatus = False
    return [essen,mensastatus]