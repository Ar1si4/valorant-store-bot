import json
import random

import sqlalchemy.orm.scoping

from database.user import RiotAccount

with open("proxies.json", "r", encoding="utf-8") as f:
    ips = json.load(f)


def get_ip(session: sqlalchemy.orm.Session, is_premium: bool, account: RiotAccount):
    if is_premium:
        if not account.proxy_ip:
            new_ip = random.choice(ips[6000:])
            if session.query(RiotAccount).filter(RiotAccount.proxy_ip == new_ip).count() != 0:
                return get_ip(session, is_premium, account)
            account.proxy_ip = new_ip
            session.commit()
            return new_ip
        else:
            if account.proxy_ip in ips:
                return account.proxy_ip
            account.proxy_ip = ""
            session.commit()
            return get_ip(session, is_premium, account)
    return random.choice(ips[:14000])


def get_proxy_url(session: sqlalchemy.orm.Session, is_premium: bool, account: RiotAccount):
    ip = get_ip(session, is_premium, account)
    return {
        "http": f"http://lum-customer-hl_e6fa5f6e-zone-valorant_store_bot-ip-{ip}:i8j8xfmwebi0@zproxy.lum-superproxy.io:22225",
        "https": f"https://lum-customer-hl_e6fa5f6e-zone-valorant_store_bot-ip-{ip}:i8j8xfmwebi0@zproxy.lum-superproxy.io:22225"
    }
