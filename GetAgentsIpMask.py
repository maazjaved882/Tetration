#!/usr/bin/env python
# coding: utf-8

# In[6]:


from tetpyclient import RestClient
from requests import Response
from json import loads, dumps
import pandas as pd
import json
from pandas.io.json import json_normalize
import urllib3


urllib3.disable_warnings()


# In[7]:


# step 1, getting data from api
api_endpoint = "https://atl1r1002-tet01.delta.com/"
try:
  credentials_file = 'credentials.json'
  rc = RestClient(api_endpoint, disable_status=False, verify=False, credentials_file=credentials_file)

except FileNotFoundError:
  print('Please add api_credentials.json file.')
  sys.exit()


# In[8]:


def get_sensors():
    '''
    Get sensors with API
    '''
    
    resp = rc.get('/sensors')
    if resp.status_code != 200:
            raise Exception(resp.status_code, resp.text)

    sensors = loads(resp.content)   
    
    sensors_df = json_normalize(sensors['results'], record_path='interfaces', meta=['host_name'],
                                record_prefix='_', errors='ignore')
    sensors_df.rename(columns={'host_name':'Hostname', '_ip':'IP', '_netmask':'Netmask', '_vrf':'Tenant'},
                      inplace=True)
    sensors_df = sensors_df[['Hostname', 'IP', 'Netmask', 'Tenant']]
    sensors_df.drop( sensors_df[ sensors_df['IP'] == '127.0.0.1' ].index , inplace=True)
    

    droplist = ['fd80','fe80', '::', '169.254.', '2001']

    for i  in droplist:
        sensors_df = sensors_df[sensors_df["IP"].str.startswith(i)==False]

    return sensors_df


# In[9]:


sensors_df = get_sensors()


# In[10]:


sensors_df.head(15)


# In[11]:


sensors_df.to_csv('AgentsIpMask.csv', index=False)


# In[ ]:




