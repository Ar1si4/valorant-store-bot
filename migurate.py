from typing import List

from database import User as UserNew
from database_old import User as UserOld
from database import session as sessionN
from database_old import session as sessionOld
from database import RiotAccount

olds: List[UserOld] = sessionOld.query(UserOld).all()
new_users = []
for old in olds:
    if not old.riot_userid:
        continue
    new_users.append(UserNew(
        id=old.uuid,
        riot_accounts=[
            RiotAccount(
                username=old.riot_userid,
                password=old.riot_password,
                region="ap",
            )
        ]
    ))
print(len(new_users))
sessionN.add_all(new_users)
sessionN.commit()
