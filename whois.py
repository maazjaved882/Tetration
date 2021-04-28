import json
import csv
import argparse
from ipwhois import IPWhois
import pandas
import ipaddress
from datetime import datetime, timedelta


def get_args():
    parser = argparse.ArgumentParser(description='query whois for IP address info')
    parser.add_argument('-f', dest='file', help='file with IPs to query', required=True)
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    with open(args.file, encoding='ascii', errors='ignore') as file:
        ips = list(set(filter(None, file.read().split('\n'))))

    print(ips)
    start = (datetime.now() - timedelta(days=0)).strftime('%Y-%m-%dT%H:%M:%S-00:00')

    asns = []
    cidrs = []
    filters = []

    filter_names = set()
    unique = set()
    count = 0
    lookup_count = 0
    for ip in ips:
        count += 1
        lookup = True
        if ipaddress.ip_network(ip).is_global and ipaddress.ip_address(ip) not in ipaddress.ip_network('192.0.0.0/24'):
            for cidr in unique:
                if ipaddress.ip_address(ip) in ipaddress.ip_network(cidr):
                    lookup = False
            if lookup:
                lookup_count += 1
                print(str(count) + '/' + str(len(ips)) + ' ' + str(lookup_count) + ' ' + ip)

                try:
                    obj = IPWhois(ip)
                    asn = obj.lookup_whois()
                    asns.append(asn)
                    nets = asn['nets']
                    for net in nets:
                        for cidr in [x.strip() for x in net['cidr'].split(',')]:

                            if cidr not in unique and cidr != '0.0.0.0/0':
                                unique.add(cidr)
                                new = net.copy()
                                new['cidr'] = cidr

                                if new['description'] is not None and any(c.isalpha() for c in new['description'].split('\n')[0].split(',')[0]):
                                    new['filter'] = ' '.join(new['description'].split('\n')[0].split(',')[0].split())
                                elif new['name'] is not None:
                                    new['filter'] = new['name']
                                else:
                                    new['filter'] = None

                                if new['filter'] is not None:
                                    print('  ' + new['cidr'] + ' ' + new['filter'])
                                    filter_names.add(new['filter'])
                                cidrs.append(new)
                except:
                    print('invalid ip' + ' ' + ip)

    for filter_name in filter_names:
        filters.append([filter_name, 'Default', 'user_whois_filter=' + filter_name])

    file = args.file.split('.')[0]

    pandas.read_json(json.dumps(asns)).to_csv(file + '_asn.csv')

    cidrs_df = pandas.read_json(json.dumps(cidrs))
    cidrs_df = cidrs_df.add_prefix('whois_')
    cidrs_df.rename(columns={'whois_cidr': 'IP'}, inplace=True)
    cidrs_df.to_csv(file + '_annotations.csv', index=False)

    writer = csv.writer(open(file + '_filters.csv', 'w', newline=''))
    writer.writerows(filters)
    stop = (datetime.now() - timedelta(days=0)).strftime('%Y-%m-%dT%H:%M:%S-00:00')
    print('start ' + start)
    print('stop ' + stop)


if __name__ == '__main__':
    main()
