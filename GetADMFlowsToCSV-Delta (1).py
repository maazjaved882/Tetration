#!/usr/bin/env python
# coding: utf-8

# In[15]:


from tetpyclient import RestClient
from requests import Response
from json import loads, dumps
from datetime import datetime, timedelta, timezone
from dateutil.parser import parse
import pandas as pd 
import json 
from pandas.io.json import json_normalize
import re
from datetime import datetime
import os
import sys
import urllib3
from tabulate import tabulate
import numpy as np


urllib3.disable_warnings()


# In[16]:


# step 1, getting data from api
api_endpoint = "https://atl1r1002-tet01.delta.com"
try:
  credentials_file = 'credentials.json'
  rc = RestClient(api_endpoint, disable_status=False, verify=False, credentials_file=credentials_file)

except FileNotFoundError:
  print('Please add api_credentials.json file.')
  sys.exit()


# In[17]:


root_scope_name = ''


# In[18]:


def get_workspaces():
    '''
    Get Workspaces IDs from API
    '''

    resp = rc.get('/applications')
    if resp.status_code != 200:
        raise Exception(resp.status_code, resp.text)

    workspaces = loads(resp.text)
    app_df = pd.DataFrame(workspaces, columns=['name', 'id', 'latest_adm_version'])

    return app_df


# In[19]:


def getUserInput():
    wheaders = ['Workspace', 'ID', 'Latest version']
    print('\n')
    print(tabulate(app_df, headers=wheaders,tablefmt='psql'))

    version_list = list(app_df['latest_adm_version'])
    version_list = set(version_list)
    if 0 in version_list:
        version_list.remove(0)
    
    while True:
        try:
            ws_select = int((input('\nPlease Select Workspace:')))
            break
        except ValueError:
            print('Intiger and choose workspace with Latest version number from {} , please.'.format(version_list))

    application_id = app_df.iloc[ws_select]['id']
    application_name = app_df.iloc[ws_select]['name']
    version_num = int(app_df.iloc[ws_select]['latest_adm_version'])
    
    print('='*40)
    print('\n')
    print('You selected:')
    print('\n')
    print('\tWorkspace: {}'.format(application_name))
    print('\tID: {}'.format(application_id))
    print('\tLatest version: {}'.format(version_num))
    print('\n')
    print('='*40)

    if version_num == 0:
        print('Please Select Workspace with Latest version different than 0.')
        print('Conversations are only available for versions generated via an ADM run.')
        print('\n')
        print('\n')
        print('\n')
        sys.exit()


    return application_name, application_id, version_num


# In[20]:


def get_app_filters():


    resp = rc.get('/filters/inventories')
    if resp.status_code != 200:
        raise Exception(resp.status_code, resp.text)
    app_filters = loads(resp.text)

    dff = pd.DataFrame(app_filters, columns=['id', 'short_name', 'name'])

    dff = dff[['id', 'name']]
    filters_dict = dict(sorted(dff.values.tolist()))

    return filters_dict


# In[21]:


def get_app_scopes():


    resp = rc.get('/app_scopes')
    if resp.status_code != 200:
        raise Exception(resp.status_code, resp.text)
    app_scopes = loads(resp.text)

    dfs = pd.DataFrame(app_scopes, columns=['id', 'short_name', 'name'])

    dfs = dfs[['id', 'name']]
    scopes_dict = dict(sorted(dfs.values.tolist()))

    return scopes_dict


# In[22]:


def get_sensors():
    '''
    Get sensors with API
    '''
    
    resp = rc.get('/sensors')
    if resp.status_code != 200:
            raise Exception(resp.status_code, resp.text)

    sensors = loads(resp.content)
    
    sensors_df1 = json_normalize(sensors['results'])

    sensors_df1.rename(columns={'host_name':'Hostname'}, inplace=True) 
        
    
    
    sensors_df = json_normalize(sensors['results'], record_path='interfaces', meta=['host_name'], 
                                record_prefix='_', errors='ignore')
    sensors_df.rename(columns={'host_name':'Hostname', '_ip':'IP', }, inplace=True) 
    sensors_df = sensors_df[['IP', 'Hostname']]
    sensors_df.drop( sensors_df[ sensors_df['IP'] == '127.0.0.1' ].index , inplace=True)


    droplist = ['fe80', '::', '169.254.']

    for i  in droplist:
        sensors_df = sensors_df[sensors_df["IP"].str.startswith(i)==False]

    hostname_ip_dict = dict(sorted(sensors_df.values.tolist()))

    return hostname_ip_dict, sensors_df, sensors_df1


# In[46]:


def get_inventory():
    
    req_payload = {"filter": {}, "dimensions": ["user_orchestrator_system/machine_name", "ip",
                                                "user_orchestrator_system/dns_name"], "limit": 50000, "offset": ''}
    
    inventory_results = rc.post('/inventory/search', json_body=dumps(req_payload))
    
    if inventory_results.status_code == 200:
        parsed_resp = loads(inventory_results.content)
        resp = parsed_resp["results"]
        while 'offset' in parsed_resp:
            pr_offset = (parsed_resp)['offset']
            req_payload["offset"] = (parsed_resp)['offset']
            inventory_results = rc.post('/inventory/search', json_body=dumps(req_payload))
            parsed_resp = loads(inventory_results.content)
            resp1 = parsed_resp["results"]
            resp.extend(resp1)

    
    df_inv = pd.DataFrame(resp)
   
    df_inv1 = df_inv[['ip', 'user_orchestrator_system/dns_name']]
    df_inv2 = df_inv[['ip', 'user_orchestrator_system/machine_name']]


    ip_dns_name = dict(df_inv1.values.tolist())
    ip_machine_name = dict(df_inv2.values.tolist())
    
    #ip_dns_name = dict((k, v) for k, v in ip_dns_name.items() if v)
    #ip_machine_name = dict((k, v) for k, v in ip_machine_name.items() if v)

    return ip_dns_name, ip_machine_name


# In[47]:


def get_app_details(application_id):
    # Get ADM DEtails

    policies_results = rc.get('/applications/{}/details'.format(application_id))
    
    if policies_results.status_code == 200:
        adm_details = loads(policies_results.content)

    id_scope_filter_dict = {}

    for i in adm_details['inventory_filters']:
        id_scope_filter_dict[i['id']] = i['name']
    
    if 'clusters' in adm_details.keys():
        for i in adm_details['clusters']:
            id_scope_filter_dict[i['id']] = i['name']

    return adm_details, id_scope_filter_dict


# In[48]:


def get_conversations():
    '''
    Get ADM conversations from API
    '''
    
    req_payload = {
                    "version": version_num,
                     "filter": {},
                     "limit" : 5000,
                     "offset": ''
                   }
        
    conversations_results = rc.post('/conversations/{}'.format(application_id), json_body=dumps(req_payload))
    
    if conversations_results.status_code == 200:
        parsed_resp = loads(conversations_results.content)
        resp = parsed_resp["results"]
        while 'offset' in parsed_resp:
            pr_offset = (parsed_resp)['offset']
            print('collecting conversations, offset:', pr_offset[-10:])
            req_payload["offset"] = (parsed_resp)['offset']
            conversations_results = rc.post('/conversations/{}'.format(application_id), json_body=dumps(req_payload))
            parsed_resp = loads(conversations_results.content)
            resp1={}
            resp1 = parsed_resp["results"]
            resp.extend(resp1)
        else:
            print("Done collecting conversations.", len(resp),"conversations exported.")
        
    df = pd.DataFrame(resp)
    df = df[['src_ip', 'dst_ip', 'protocol', 'port', 'byte_count' ]]
    df.rename(columns={'src_ip':'Consumer Address',  
                       'dst_ip':'Provider Address',
                       'protocol':'Protocol', 'port':'Port', 'byte_count':'Byte Count',}, inplace=True)
    df['Consumer Hostname'] = df['Consumer Address']
    df['Consumer Machinename'] = df['Consumer Address']
    df['Consumer DNS'] = df['Consumer Address']

    df['Provider Hostname'] = df['Provider Address']
    df['Provider Machinename'] = df['Provider Address']
    df['Provider DNS'] = df['Provider Address']

    df = df[['Consumer Address', 'Consumer Hostname','Consumer Machinename', 'Consumer DNS', 'Provider Address',
            'Provider Hostname',  'Provider Machinename', 'Provider DNS', 'Protocol', 'Port', 'Byte Count']]
    #all_ip_dict = {**app_filters, **id_scope_filter_dict, **scopes_dict}
    
    df['Consumer Hostname'] = df['Consumer Hostname'].map(hostname_ip_dict)
    df['Provider Hostname'] = df['Provider Hostname'].map(hostname_ip_dict)
    df['Consumer Machinename'] = df['Consumer Machinename'].map(ip_machine_name)
    df['Consumer DNS'] = df['Consumer DNS'].map(ip_dns_name)
    df['Provider Machinename'] = df['Provider Machinename'].map(ip_machine_name)
    df['Provider DNS'] = df['Provider DNS'].map(ip_dns_name)
   
    return df


# In[49]:


if __name__ == '__main__':
    app_df = get_workspaces()
    app_filters = get_app_filters() 
    scopes_dict = get_app_scopes()
    hostname_ip_dict, sensors_df, sensors_df1 = get_sensors()
    application_name, application_id, version_num = getUserInput()
    appdetails , id_scope_filter_dict = get_app_details(application_id)
    ip_dns_name, ip_machine_name = get_inventory()
    conv_df = get_conversations()
    conv_df.to_csv('{}.csv'.format(application_name), index=False)


# In[ ]:




