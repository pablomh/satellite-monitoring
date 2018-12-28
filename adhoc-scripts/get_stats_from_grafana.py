#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

#curl 'http://c03-h30-r620.rdu.openstack.engineering.redhat.com:11202/api/datasources/proxy/1/render'
#   -H 'Accept: application/json, text/plain, */*'
#   -H 'Accept-Language: en-US,en;q=0.5'
#   --compressed
#   -H 'Content-Type: application/x-www-form-urlencoded'
#   --data $'target=alias(satellite62.cloud02-sat-vm1_rdu_openstack_engineering_redhat_com.load.load.shortterm%2C%20\'1m%20avg\')&target=alias(satellite62.cloud02-sat-vm1_rdu_openstack_engineering_redhat_com.load.load.midterm%2C%20\'5m%20avg\')&target=alias(satellite62.cloud02-sat-vm1_rdu_openstack_engineering_redhat_com.load.load.longterm%2C%20\'15m%20avg\')&from=-5min&until=now&format=json&maxDataPoints=1908'

import argparse
import logging
import configparser
import requests
import statistics

parser = argparse.ArgumentParser(description='Get stats from Graphite/Grafana for given interval')
parser.add_argument('from_ts', type=int,
                    help='timestamp (UTC) of start of the interval')
parser.add_argument('to_ts', type=int,
                    help='timestamp (UTC) of end of the interval')
parser.add_argument('--inventory', default='conf/inventory.ini',
                    help='Inventory where is the Graphite server defined')
parser.add_argument('--port', type=int, default=11202,
                    help='Port Grafana is listening on')
parser.add_argument('--prefix', default='satellite62',
                    help='Prefix for data in Graphite')
parser.add_argument('--debug', action='store_true',
                    help='Debug mode')
args = parser.parse_args()

if args.debug:
    logging.basicConfig(level=logging.DEBUG)

logging.debug("Arguments: %s" % args)

# Metrics we are interested in and their aliases
targets = {
    'load.load.shortterm': 'load 1m avg',
    'load.load.midterm': 'load 5m avg',
    'load.load.longterm': 'load 15m avg',
}
logging.debug("Metrics: %s" % targets)

# What is the Graphite server we should talk to
cfg = configparser.ConfigParser()
cfg.read(args.inventory)
graphite = cfg.items('graphite')[0][0].split()[0]
logging.debug("Graphite server: %s" % graphite)

# Metadata for the request
headers = {
    'Accept': 'application/json, text/plain, */*',
}
params = {
    'target': ["alias(%s.cloud02-sat-vm1_rdu_openstack_engineering_redhat_com.%s, '%s')" % (args.prefix, k, v) for k,v in targets.items()],
    'from': args.from_ts,
    'until': args.to_ts,
    'format': 'json',
}
url = "http://%s:%s/api/datasources/proxy/1/render" % (graphite, args.port)

r = requests.get(url=url, headers=headers, params=params)
if not r.ok:
    logging.error("URL = %s" % r.url)
    logging.error("headers = %s" % r.headers)
    logging.error("status code = %s" % r.status_code)
    logging.error("text = %s" % r.text)
    raise Exception("Request failed")
data = r.json()

for d in data:
    d_plain = [i[0] for i in d['datapoints']]
    d_min = min(d_plain)
    d_max = max(d_plain)
    d_mean = statistics.mean(d_plain)
    d_median = statistics.median(d_plain)
    d_pstdev = statistics.pstdev(d_plain)
    d_pvariance = statistics.pvariance(d_plain)
    print([d['target'], d_min, d_max, d_mean, d_median, d_pstdev, d_pvariance])
