"""
This file contains classes, which are mapped directly to a database.
The classes can be in it's own files as well but the order of import matters:
'DB' has to be declared, before the models can be imported 
(since they extend the DB class).
But the 'engine' and 'session' has to be created, 
after the classes are importet.
The engine is the binding to the database file, the session the object we use
to read and write thorugh the engine. Once created the session acts 
like a static variable of the models module (this file) and can be directly
imported from anywhere, after its created once (by importing the models module)
No need to understand this in detail, if you just don't change the order of 
class definintions and imports. The abstract classes we define here can later
be handled as common objects/classes in python, but since they contain also the
structure of the database they are often called models instead of classes.

Just one thing more to understand the way this works, the DB class adds a lot of 
functions and variables which we don't see here, they work in the background
and handle the db-related stuff. From outside this models we can acess this 
"hidden" functions anyway as model.anyhiddenfunction(). 
The SQL-Datatypes (String, Boolean, Integer, Time ...) we imported with 
sqlalchemy.* work in an equal manner:
They are an abstraction of the default python dtypes (Str, Int dt.Time ...),
with some added features for example the mysql querystrings to handle them.
Note it's important to care about * imports as u can C (dt.Time != sqla.Time)
"""

import datetime as dt

from sqlalchemy import *  # serves alternative datatypes and (db-)Columns
from sqlalchemy.ext.declarative import declarative_base  # this creates the DB
from sqlalchemy.orm import sessionmaker  # function to setup a DB-Session
from sqlalchemy.orm import scoped_session  # try to avoid thread error

# Create the abstract DB-'class' before defining our models:
DB = declarative_base()  # DB is also written as 'Base' in many tutorials

# Now we can import or define any classes we want to have in our database.
# Create a mapped class such as a normal class, but:
#   - inherit the DB class: class Classname(DB): 
#   - just ignore the def __init__() this is handled by DB
#   - set the tablename to make sql-db readable (can be equal to class name)
#   - define any object related variables as class variabels (without self)
#   - use the Colum() class and pass datatype and options for each variable
#   - TODO: I have to checkout how to handle functions in this class

# list of sql-dtypes http://docs.sqlalchemy.org/en/latest/core/type_basics.html






class User(DB):
    """ A abstract User-Class (model) that is linked to a database file, by
    sqlalchemy. The user object can be handled in the same way as before.
    So changes don't affect the user it self only the db_handler.py related
    stuff.
    """

    __tablename__ = 'user'
    chat_id = Column(Integer, primary_key=True)  # Deal?
    first_name = Column(String(200), nullable=True)
    # You can pass a maxlength, but dont have to
    abo = Column(Boolean, default=False)  # guess u got this
    abo_time = Column(Time, default=dt.time(9,15,0,0))  # this is clear too?
    alarm_status = Column(Boolean, default=False)  # should be clear as well..
    mensa_id = Column(Integer, default=201) # for later use 167 for uni mensa
    fav_food = Column(String(350), default='weihnachtsessen,grünkohl')

    # define non-database stuff just as common variables (without Column())
    # job_abo = None
    # job_fav_food_alarm = None
    # job_fav_food_list = None

    # add function is not longer needed, get_abo_timer is also not needed since
    # it's stored as time object in the db not as string
    # if you ignore the comments, the class looks pretty much like the old one
    # + all the Column(...) declarations and - the 2 functions




#setting up the engine and session which we use to sync from outside
engine = create_engine('sqlite:///sql.db')  # File read/writer
# setup tables: (the metadata is set by models the moment they expand DB)
DB.metadata.create_all(engine, checkfirst=True) #check aviods struct change?
# maybe also session = sessionmaker() works if only one session is needed
factory = sessionmaker(bind=engine)
session = scoped_session(factory)  # use this session everywhere where its imported
