import json
import csv
import argparse
from tetpyclient import RestClient
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_args():
    parser = argparse.ArgumentParser(description='For selected applications, query convos with consumer/provider cluster/filter/scope. Output CSV per application.')
    parser.add_argument('-a', dest='applications', help='comma-separated adm workspaces OPTIONAL', required=False)
    parser.add_argument('-E', dest='endpoint', help='API endpoint (Tetration IP or hostname) OPTIONAL defualt: "api_endpoint" from ./endpoint.json')
    parser.add_argument('-C', dest='credentials', help='api_credentials.json (download at Settings > API Key > Creat API Key) OPTIONAL', required=False)
    parser.add_argument('-k', dest='keyword', help='filter convos by keyword in consumer_filter_name or provider_filter_name (e.g. "NONPROD") OPTIONAL', required=False)
    args = parser.parse_args()
    return args


def main():
    args = get_args()

    # get endpoint
    if args.endpoint is not None:
        endpoint = 'https://' + args.endpoint + '/'
    else:
        endpoint = json.loads(open('../endpoint.json', 'r').read())['api_endpoint']

    # get credentials
    if args.credentials is not None:
        credentials = args.credentials
    else:
        credentials = '../credentials.json'

    rc = RestClient(endpoint, credentials_file='./' + credentials, verify=False)

    # get scopes
    resp = rc.get('/app_scopes/')
    if resp.status_code == 200:
        scopes = json.loads(resp.content)
    else:
        raise Exception(resp.text)

    # get inventory filters
    resp = rc.get('/filters/inventories/')
    if resp.status_code == 200:
        inventory_filters = json.loads(resp.content)
    else:
        raise Exception(resp.text)

    # get applications
    if args.applications is not None:
        applications = [x.strip() for x in args.applications.split(',')]
    else:
        print('\napplications:')
        resp = rc.get('/applications/')
        if resp.status_code == 200:
            parsed_resp = json.loads(resp.content)
            for i in range(len(parsed_resp)):
                print(' ' + str(i) + '\t' + parsed_resp[i]['name'])

        else:
            raise Exception(resp.text)

    response = input('\nenter applications (comma-separated value or range): ').split(',')

    choices = ''
    for x in response:
        if choices == '':
            if '-' in x:
                choices = ','.join([str(x) for x in list(range(int(x.split('-')[0]), int(x.split('-')[1]) + 1))])
            else:
                choices = x
        else:
            if '-' in x:
                choices += ',' + ','.join([str(x) for x in list(range(int(x.split('-')[0]), int(x.split('-')[1]) + 1))])
            else:
                choices += ',' + x

    applications = [parsed_resp[int(x)]['name'] for x in choices.split(',')]

    for application in applications:
        rows = []
        headers = []
        for item in parsed_resp:
            if item['name'] == application:
                # req_payload = {
                #     'version': item['latest_adm_version'],
                #     'dimensions': [],
                #     'metrics': []
                # }

                # # get conversations
                # resp = rc.post('/conversations/' + item['id'], json_body=json.dumps(req_payload), timeout=90.0)
                # if resp.status_code == 200:
                #     convos = json.loads(resp.content)['results']
                # else:
                #     raise Exception(resp.text)

                # get convos
                offset = ''
                convos = []
                while offset is not None:
                    req_payload = {
                        'version': item['latest_adm_version'],
                        'offset': offset,
                        'dimensions': [],
                        'metrics': []
                    }
                    resp = rc.post('/conversations/' + item['id'], json_body=json.dumps(req_payload), timeout=90.0)
                    if resp.status_code == 200:
                        parsed_resp = json.loads(resp.content)
                    else:
                        print('  unable to query convos')
                        raise Exception(resp.text)
                    if 'offset' in parsed_resp:
                        offset = parsed_resp['offset']
                    else:
                        print('')
                        offset = None
                    convos += parsed_resp['results']

                if len(convos) > 0:
                    headers = list(convos[0].keys())

                    # get application details
                    resp = rc.get('/applications/' + item['id'] + '/details', timeout=30.0)
                    if resp.status_code == 200:
                        application_details = json.loads(resp.content)
                    else:
                        raise Exception(resp.text)

                    for convo in convos:
                        row = []
                        for key in convo.keys():
                            row.append(convo[key])

                        # get consumer filter name
                        consumer_filter_name = ''
                        if convo['consumer_filter_id'] in [x['id'] for x in scopes]:
                            consumer_filter_name = scopes[[x['id'] for x in scopes].index(convo['consumer_filter_id'])]['name']
                        elif convo['consumer_filter_id'] in [x['id'] for x in inventory_filters]:
                            consumer_filter_name = inventory_filters[[x['id'] for x in inventory_filters].index(convo['consumer_filter_id'])]['name']
                        elif 'clusters' in application_details.keys():
                            clusters = application_details['clusters']
                            if convo['consumer_filter_id'] in [x['id'] for x in clusters]:
                                consumer_filter_name = clusters[[x['id'] for x in clusters].index(convo['consumer_filter_id'])]['name']

                        # get provider filter name
                        provider_filter_name = ''
                        if convo['provider_filter_id'] in [x['id'] for x in scopes]:
                            provider_filter_name = scopes[[x['id'] for x in scopes].index(convo['provider_filter_id'])]['name']
                        elif convo['provider_filter_id'] in [x['id'] for x in inventory_filters]:
                            provider_filter_name = inventory_filters[[x['id'] for x in inventory_filters].index(convo['provider_filter_id'])]['name']
                        elif 'clusters' in application_details.keys():
                            clusters = application_details['clusters']
                            if convo['provider_filter_id'] in [x['id'] for x in clusters]:
                                provider_filter_name = clusters[[x['id'] for x in clusters].index(convo['provider_filter_id'])]['name']

                        if args.keyword is not None:
                            if args.keyword in consumer_filter_name or  args.keyword in provider_filter_name:
                                row.append(consumer_filter_name)
                                row.append(provider_filter_name)
                                rows.append(row)
                        else:
                            row.append(consumer_filter_name)
                            row.append(provider_filter_name)
                            rows.append(row)

        headers.append('consumer_filter_name')
        headers.append('provider_filter_name')
        rows.insert(0, headers)

        writer = csv.writer(open(application.replace(' ', '_').replace(':','_') + '.csv', 'w', newline=''))
        writer.writerows(rows)
        print(' ' + application.replace(' ', '_').replace(':','_') + '.csv created')
    print('\nDone!\n')


if __name__ == '__main__':
    main()
