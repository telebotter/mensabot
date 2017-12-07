from dbhelper import DBHelper
import datetime

class User():
    '''user objekt mit den einträgen '''

    def __init__(self,chat_id):
        self.first_name = 'default'
        self.chat_id = chat_id
        self.fav_food = 'Grünkohl'
        self.abo = False
        self.abo_time = '0915'
        self.job_abo = None


    def add(self):
        db = DBHelper(setup = False)
        db.add_item(self)

    def get_abo_time(self):
        '''insert string 'HHMM' and returns datetime.time object for job_queue'''
        time = datetime.datetime.strptime(self.abo_time, '%H%M').time()
        return time





