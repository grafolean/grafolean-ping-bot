from collections import defaultdict
from multiping import MultiPing
import os
import requests
import socket
import time

N_PINGS = 3

# This is copy-pasted from multiping package; the reason is that we need to get MultiPing
# instance, because it holds the IP addresses which correspond to the addresses we wanted
# pinged - and the key in ping results is the IP.
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

def get_addr_for_ip_dict(addrs, mp):
    # This is complicated, and a hack. Still... mp (MultiPing instance) holds two lists,
    # self._dest_addrs and self._unprocessed_targets. List _unprocessed_targets has the addresses
    # that couldn't be resolved. Others were resolved, and _dest_addrs has the IPs in the same
    # order as original addresses.
    resolved_addrs = [a for a in addrs if a not in mp._unprocessed_targets]
    ip_to_addr = {k: v for k, v in zip(mp._dest_addrs, resolved_addrs)}
    return ip_to_addr

def do_ping(addrs):
    results = defaultdict(list)
    mp = None
    ip_to_addr = {}
    for i in range(N_PINGS):
        print(".")
        responses, no_responses, mp = multi_ping(addrs, timeout=2, retry=3, ignore_lookup_errors=True)

        # Some addresses (like demo.grafolean.com) resolve to multiple IPs, so each call to multi_ping will
        # resolve differently - we must find the new IP addresses every time:
        ip_to_addr = get_addr_for_ip_dict(addrs, mp)

        for no_resp in no_responses:
            addr = ip_to_addr.get(no_resp, no_resp)
            results[addr].append(None)
        for resp, t in responses.items():
            addr = ip_to_addr.get(resp, resp)
            results[addr].append(t)

        if i < N_PINGS - 1:
            time.sleep(1)
    return dict(results)

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

if __name__ == "__main__":
    addrs = ["8.8.8.8", "youtube.com", "127.0.0.1", "demo.grafolean.com", "grafolean.com", "whateverdoeesndfexist.com"]
    results = do_ping(addrs)
    send_results_to_grafolean(os.environ.get('BACKEND_URL'), 1, os.environ.get('BOT_TOKEN'), results)
