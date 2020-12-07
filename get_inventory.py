import json
import argparse
from tetpyclient import RestClient
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import pandas


def get_args():
    parser = argparse.ArgumentParser(description='Get inventory for scope')
    parser.add_argument('-s', dest='scope', help='scope name to query REQUIRED', required=False)
    parser.add_argument('-f', dest='filter', help='filter OPTIONAL (e.g. user_orchestrator_system/orch_type=vcenter)', required=False)
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    rc = RestClient(json.loads(open('endpoint.json', 'r').read())['api_endpoint'], credentials_file='./credentials.json', verify=False)

    args = get_args()

    if args.filter is not None:
        if '=' in args.filter:
            filter = {'type': 'eq', 'field': args.filter.split('=')[0], 'value': args.filter.split('=')[1]}
        else:
            filter = {}
    else:
        filter = {}

    count = 0
    total = 0

    offset = ''
    results = []

    body = {
        'filter': filter,
        'scopeName': args.scope,
    }

    resp = rc.post('/inventory/count', json_body=json.dumps(body), timeout=90.0)

    if resp.status_code == 200:
        count = json.loads(resp.content)['count']
    else:
        print('unable to get count')
        raise Exception(resp.text)

    if count > 0:

        while offset is not None:
            body = {
                'filter': filter,
                'scopeName': args.scope,
                'offset': offset,
            }

            resp = rc.post('/inventory/search', json_body=json.dumps(body), timeout=90.0)

            if resp.status_code == 200:
                parsed_resp = json.loads(resp.content)
                total += len(parsed_resp['results'])
                print('%d%%' % (total / count * 100) + ' %d' % total + '/' + str(count), end='\r')
            else:
                print('unable to get inventory')
                raise Exception(resp.text)

            if 'offset' in parsed_resp:
                offset = parsed_resp['offset']
            else:
                print('')
                offset = None
            results += parsed_resp['results']

        pandas.read_json(json.dumps(results)).to_csv('inventory.csv')

        print('created inventory.csv\n')

    else:
        print('no match\n')


if __name__ == '__main__':
    main()
