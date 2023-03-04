from functions import *
from requests.auth import HTTPBasicAuth

config_data = read_config_ini()

jira_kosin_url = config_data['JIRA Kosin url']
kosin_user = config_data['Kosin user']
kosin_password = config_data['Kosin password']
key_dict = eval(config_data['key_dict'])
issuetype_dict = eval(config_data['issuetype_dict'])
serviceline_dict = eval(config_data['serviceline_dict'])

# make the connection to JIRA Kosin
jira_response = connect_to_jira(jira_kosin_url, kosin_user, kosin_password)
auth = HTTPBasicAuth(kosin_user, kosin_password)

workload_list = eval(open('worklogs_filtered.txt', 'r').read())

insert_tickets(jira_response, workload_list, jira_kosin_url, auth, kosin_user, key_dict, issuetype_dict, serviceline_dict)

