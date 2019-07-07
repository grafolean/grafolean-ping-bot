from apscheduler.schedulers.blocking import BlockingScheduler
from collections import defaultdict
from colors import color
import logging
from multiping import MultiPing
import os
from pytz import utc
import requests
import socket
import time


logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logging.addLevelName(logging.DEBUG, color("DBG", 7))
logging.addLevelName(logging.INFO, "INF")
logging.addLevelName(logging.WARNING, color('WRN', fg='red'))
logging.addLevelName(logging.ERROR, color('ERR', bg='red'))
log = logging.getLogger("{}.{}".format(__name__, "base"))


N_PINGS = 3


class Collector(object):

    @staticmethod
    def get_bot_config_from_grafolean(base_url, bot_token):
        # !!! dummy:
        user_id = 123
        addrs = ["8.8.8.8", "youtube.com", "127.0.0.1", "demo.grafolean.com", "grafolean.com", "whateverdoeesndfexist.com"]
        config_per_account = {
            1: [{"address": address, "interval": 60, "retries": 2, "timeout": 30, "n_packets": 3} for address in addrs],
        }
        return user_id, config_per_account

        # !!! backend doesn't support this yet:
        r = requests.get('{}/api/profile/accounts/?b={}'.format(base_url, bot_token))
        if r.status_code != 200:
            raise Exception("Invalid bot token or network error, got status {} while retrieving /profile/accounts".format(r.status_code))
        json = r.json()
        user_id = json["user_id"]
        accounts_ids = [a["id"] for a in json["list"]]

        # for each account that we have some permission to access, find out what the config (for our bot) is, so we know what data to collect:
        config = {}
        for account_id in accounts_ids:
            r = requests.get('{}/api/profile/accounts/{}/?b={}'.format(base_url, account_id, bot_token))
            if r.status_code != 200:
                raise Exception("Invalid bot token or network error, got status {} while retrieving /profile/accounts/{}".format(r.status_code, account_id))
            json = r.json()
            if not json["config"]:  # there is no config for our bot for this account - skip it
                continue
            config[account_id] = json

        return user_id, config


    @staticmethod
    def send_results_to_grafolean(base_url, account_id, bot_token, results):
        url = '{}/api/accounts/{}/values/?b={}'.format(base_url, account_id, bot_token)
        values = []
        for ip in results:
            for ping_index, ping_time in enumerate(results[ip]):
                values.append({
                    'p': 'ping.{}.{}.success'.format(ip.replace('.', '_'), ping_index),
                    'v': 0 if ping_time is None else 1,
                })
                if ping_time is not None:
                    values.append({
                        'p': 'ping.{}.{}.rtt'.format(ip.replace('.', '_'), ping_index),
                        'v': ping_time,
                    })
        print("Sending results to Grafolean")
        r = requests.post(url, json=values)
        print(r.text)
        r.raise_for_status()


class PingCollector(Collector):

    def __init__(self, backend_url, bot_token):
        self.backend_url = backend_url
        self.bot_token = bot_token

    def run(self):
        # get config:
        user_id, config_per_account = Collector.get_bot_config_from_grafolean(self.backend_url, self.bot_token)

        # initialize a scheduler:
        job_defaults = {
            'coalesce': True,  # if multiple jobs "misfire", re-run only one instance of a missed job
            'max_instances': 10
        }
        scheduler = BlockingScheduler(job_defaults=job_defaults, timezone=utc)

        # apply config to scheduler:
        for account_id, ping_configs in config_per_account.items():
            for ping_config in ping_configs:
                kwargs = {
                    "addrs": [ping_config["address"]],
                    "account_id": account_id,
                    "n_packets": ping_config["n_packets"],
                }
                scheduler.add_job(PingCollector.do_ping, 'interval', seconds=ping_config["interval"], kwargs=kwargs)

        scheduler.start()


    # This is copy-pasted from multiping package; the reason for not using their version directly
    # is that MultiPing does DNS resolution, but when it returns results, they are tied to the IP
    # addresses instead of the addresses we supplied. Since we need the results tied to what we
    # requested, we return MultiPing instance which holds the translation table.
    @staticmethod
    def multi_ping(dest_addrs, timeout, retry=0, ignore_lookup_errors=False):
        retry_timeout = float(timeout) / (retry + 1)

        mp = MultiPing(dest_addrs, ignore_lookup_errors=ignore_lookup_errors)

        results = {}
        retry_count = 0
        while retry_count <= retry:
            # Send a batch of pings
            mp.send()
            single_results, no_results = mp.receive(retry_timeout)
            # Add the results from the last sending of pings to the overall results
            results.update(single_results)
            if not no_results:
                # No addresses left? We are done.
                break
            retry_count += 1

        return results, no_results, mp


    @staticmethod
    def get_addr_for_ip_dict(addrs, mp):
        # This is complicated, and a hack. Still... mp (MultiPing instance) holds two lists,
        # self._dest_addrs and self._unprocessed_targets. List _unprocessed_targets has the addresses
        # that couldn't be resolved. Others were resolved, and _dest_addrs has the IPs in the same
        # order as original addresses.
        resolved_addrs = [a for a in addrs if a not in mp._unprocessed_targets]
        ip_to_addr = {k: v for k, v in zip(mp._dest_addrs, resolved_addrs)}
        return ip_to_addr


    @staticmethod
    def do_ping(addrs, account_id, n_packets):
        results = defaultdict(list)
        mp = None
        ip_to_addr = {}
        for i in range(n_packets):
            print(".")
            responses, no_responses, mp = PingCollector.multi_ping(addrs, timeout=2, retry=3, ignore_lookup_errors=True)

            # Some addresses (like demo.grafolean.com) resolve to multiple IPs, so each call to multi_ping will
            # resolve differently - we must find the new IP addresses every time:
            ip_to_addr = PingCollector.get_addr_for_ip_dict(addrs, mp)

            for no_resp in no_responses:
                addr = ip_to_addr.get(no_resp, no_resp)
                results[addr].append(None)
            for resp, t in responses.items():
                addr = ip_to_addr.get(resp, resp)
                results[addr].append(t)

            if i < n_packets - 1:
                time.sleep(1)

        Collector.send_results_to_grafolean(os.environ.get('BACKEND_URL'), account_id, os.environ.get('BOT_TOKEN'), results)




if __name__ == "__main__":
    backend_url = os.environ.get('BACKEND_URL')
    bot_token = os.environ.get('BOT_TOKEN')
    ping_collector = PingCollector(backend_url, bot_token)
    ping_collector.run()
