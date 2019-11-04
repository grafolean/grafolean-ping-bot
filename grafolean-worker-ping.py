import os
import time
from collections import defaultdict
from colors import color
import logging
from multiping import multi_ping
from pytz import utc
import requests
import socket
import dotenv


from grafoleancollector import Collector


logging.basicConfig(format='%(asctime)s | %(levelname)s | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S', level=logging.DEBUG)
logging.addLevelName(logging.DEBUG, color("DBG", 7))
logging.addLevelName(logging.INFO, "INF")
logging.addLevelName(logging.WARNING, color('WRN', fg='red'))
logging.addLevelName(logging.ERROR, color('ERR', bg='red'))
log = logging.getLogger("{}.{}".format(__name__, "base"))


def send_results_to_grafolean(backend_url, bot_token, account_id, values):
    url = '{}/accounts/{}/values/?b={}'.format(backend_url, account_id, bot_token)

    if len(values) == 0:
        log.warning("No results available to be sent to Grafolean, skipping.")
        return

    log.info("Sending results to Grafolean")
    try:
        r = requests.post(url, json=values)
        r.raise_for_status()
        log.info("Results sent: {}".format(values))
    except:
        log.exception("Error sending data to Grafolean")


class PingCollector(Collector):

    def jobs(self):
        for entity_info in self.fetch_job_configs('ping'):
            intervals = list(set([sensor_info["interval"] for sensor_info in entity_info["sensors"]]))
            job_info = { **entity_info, "backend_url": self.backend_url, "bot_token": self.bot_token }
            job_id = str(entity_info["entity_id"])
            yield job_id, intervals, PingCollector.do_ping, job_info

    @staticmethod
    def do_ping(*args, **job_info):
        # filter out only those sensors that are supposed to run at this interval:
        affecting_intervals, = args
        hostname = job_info["details"]["ipv4"]
        cred = job_info["credential_details"]

        activated_sensors = [s for s in job_info["sensors"] if s["interval"] in affecting_intervals]
        if not activated_sensors:
            return

        # perform ping:
        values = []
        addrs = [hostname]
        timeout = float(cred.get("timeout", 2.0))
        retry = int(cred.get("retry", 0))
        n_packets = int(cred.get("n_packets", 3))
        sleep_packets = float(cred.get("sleep_packets", 1.0))
        output_path_prefix = f'entity.{job_info["entity_id"]}.ping'
        n_ok = 0
        for i in range(n_packets):
            responses, _ = multi_ping(addrs, timeout=timeout, retry=retry)

            # save results:
            if len(responses) > 0:
                values.append({'p': f"{output_path_prefix}.p{i}.ok", 'v': 1.0})
                values.append({'p': f"{output_path_prefix}.p{i}.rtt", 'v': list(responses.values())[0]})
                n_ok += 1
            else:
                values.append({'p': f"{output_path_prefix}.p{i}.ok", 'v': 0.0})
            time.sleep(sleep_packets)

        values.append({'p': f"{output_path_prefix}.success", 'v': float(n_ok) / n_packets})

        send_results_to_grafolean(job_info['backend_url'], job_info['bot_token'], job_info['account_id'], values)


if __name__ == "__main__":
    dotenv.load_dotenv()

    backend_url = os.environ.get('BACKEND_URL')
    bot_token = os.environ.get('BOT_TOKEN')
    if not backend_url or not bot_token:
        raise Exception("Please specify BACKEND_URL and BOT_TOKEN env vars.")
    jobs_refresh_interval = int(os.environ.get('JOBS_REFRESH_INTERVAL', 120))

    c = PingCollector(backend_url, bot_token, jobs_refresh_interval)
    c.execute()
