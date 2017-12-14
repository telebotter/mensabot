from models import User
from models import session
from models import Session

"""user = User()
#user.first_name = 'otto'  # must be set or error (set default or mark nullable)
#user.chat_id = 123123123
session.add(user)  # write to meta data (new user)
session.commit()  # apply changes
user.first_name = 'jens'
session.commit()
print(user.first_name)
# after a change of user variables the commit applys the change to the database
# (not only the python object), if u dont commit the user.first_name is
# changed, but a query with first_name == 'frank' would fail since thats a DB
# request and will not work until session.commit() is ran.
"""

import numpy as np

users = session.query(User).all()
usr1 = users[0]
print(usr1.first_name)
usr1.job_abo = [1,2,3,]
session.commit()

def otherwhere():
    s2 = Session()
    users = s2.query(User).all()
    usr1 = users[0]
    usr1.job_abo.append(4)

    usr1.first_name = 'hedwik'
    print(usr1.job_abo)
    print(usr1.first_name)

otherwhere()
print(usr1.job_abo)
print(usr1.first_name)

usr2 = session.query(User).all()[0]
print(usr2.job_abo)
print(usr2.first_name)
