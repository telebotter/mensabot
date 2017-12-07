import sqlite3

class DBHelper:
    """docstring for DBHelper"""
    def __init__(self, dbname='user_data.sqlite', setup = True):
        self.dbname = dbname
        self.conn = sqlite3.connect(dbname)
        if setup: self.setup()

    def setup(self):
        tblstmt = "CREATE TABLE IF NOT EXISTS user (first_name text, chat_id text, fav_food text, abo text, abo_time text)"
        itemidx = 'CREATE INDEX IF NOT EXISTS itemIndex ON user (first_name ASC)'
        ownidx = 'CREATE INDEX IF NOT EXISTS ownINDEX ON user (chat_id ASC)'
        favidx = 'CREATE INDEX IF NOT EXISTS favINDEX ON user (fav_food ASC)'
        aboidx = 'CREATE INDEX IF NOT EXISTS aboINDEX ON user (abo ASC)'
        abo_timeidx = 'CREATE INDEX IF NOT EXISTS abo_timeidxINDEX ON user (abo_time ASC)'
        self.conn.execute(tblstmt)
        self.conn.execute(itemidx)
        self.conn.execute(ownidx)
        self.conn.execute(favidx)
        self.conn.execute(aboidx)
        self.conn.execute(abo_timeidx)
        self.conn.commit()

    def add_item(self, user):
        stmt = "INSERT INTO user (first_name, chat_id,fav_food,abo,abo_time) VALUES (?, ?, ?, ?, ?)"
        args = (user.first_name, user.chat_id, user.fav_food,user.abo,user.abo_time)
        self.conn.execute(stmt, args)
        self.conn.commit()

    def delete_item(self, user):
        stmt = "DELETE FROM user WHERE chat_id =(?)"
        args = (user.chat_id, )
        self.conn.execute(stmt, args)
        self.conn.commit()

    def change_entry(self,user,collumn,value):
        stmt = "UPDATE user SET {} = (?) WHERE chat_id = (?)".format(collumn)
        args = (value, user.chat_id)
        self.conn.execute(stmt,args)
        self.conn.commit()


    def get_items(self):
        stmt = "SELECT * FROM user"
        return list(self.conn.execute(stmt))
