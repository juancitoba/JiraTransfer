import json
import datetime
from jira import JIRA
import requests
from requests.auth import HTTPBasicAuth

def connect_to_jira(url, user, password):
    jira_token = JIRA(basic_auth=(user, password),
                       options={'server': url})
    return jira_token

def get_list_source(source_user, jira_source, date_from):
    # Get the list of tickets from JIRA source
    try:
        issues_source = jira_source.search_issues(f'worklogDate >= {str(date_from)[:10]} and worklogAuthor = currentUser()',
                                                  maxResults=100)
    except Exception as e:
        print('An error occurred while trying to retrieve issues from JIRA source: %s' % e)
        return
    worklogs_filtered = []
    index = 0
    for issue in issues_source:
        print('FOUND Ticket: %s, Name: %s, Creation Date: %s, Status: %s, Type: %s'
              % (issue.key, issue.fields.summary, issue.fields.created, issue.fields.status.name, issue.fields.issuetype.name))
        try:
            worklogs = jira_source.worklogs(issue)
        except Exception as e:
            print('An error occurred while trying to retrieve worklogs from JIRA source: %s' % e)
            continue
        worklogs_filtered.append([issue.key, issue.fields.summary, issue.fields.status.name, issue.fields.issuetype.name, []])
        for worklog in worklogs:
            started = datetime.datetime.strptime(worklog.started[:10], '%Y-%m-%d')
            if worklog.author.name == source_user and started >= date_from:
                worklogs_filtered[index][4].append([str(started), convert_to_seconds(worklog.timeSpent)])
        index += 1
    save_list_to_txt('worklogs_filtered.txt', worklogs_filtered)
    jira_source.close()

def obtain_date_from():
    while True:
        user_input = input('Enter a date in YYYY/MM/DD format: ')
        try:
            date = datetime.datetime.strptime(user_input, '%Y/%m/%d')
            break
        except ValueError:
            print('Invalid date format. Please try again.')
    return date

def save_list_to_txt(name, list):
    with open(name, 'w') as f:
        f.write(str(list))
    f.close()

def convert_to_seconds(time_str):
    # Split the time string into days, hours, and minutes
    time_split = time_str.split(' ')
    # Initialize the hours variable
    days, hours, minutes = 0, 0, 0
    # Get the number of days, hours, and minutes
    for time_unit in time_split:
        if 'd' in time_unit:
            days = int(time_unit[:-1])
        elif 'h' in time_unit:
            hours += int(time_unit[:-1])
        elif 'm' in time_unit:
            minutes = int(time_unit[:-1])
    # Return the total number of seconds
    return days*24*60*60 + hours*60*60 + minutes*60

def read_config_ini():
    config_data = {}
    with open('config.ini', 'r') as f:
        for line in f:
            split_line = line.split('= ')
            config_data[split_line[0]] = split_line[1].strip()

    return config_data

def check_existing_worklog(user, worklogs, started):
    # Check if there is any existing worklog with the same date
    for worklog in worklogs:
        if worklog.author.name == user and worklog.started[:10] == started[:10]:
            return True
    return False

def insert_tickets(jira_response, workload_list, jira_kosin_url, auth, user, keys, issues, servicelines):
    status_dict = {'Ice Box': 'Open', 'Pre Analysis': 'Open', 'Prioritised': 'Open', 'Parking': 'Open',
                   'Analysis': 'Open', 'Ready For Dev': 'Open', 'In Dev': 'Developing',
                   'Ready for QA': 'Developing', 'Ready': 'Developing', 'Closed': 'Done', 'Open': 'Open',
                   'In QA': 'Developing', 'Ready for Push': 'Developing', 'In Push': 'Developing',
                   'Business Validation': 'Closed'}
    serviceline_dict = servicelines
    key_dict = keys
    issuetype_dict = issues
    #Remove some internal issues that will be handled separately
    workload_int_list = []
    workload_filtered_list = workload_list.copy()
    for item in workload_list:
        # Separate internals in a different list ['INT-136', 'INT-125', 'INT-127', 'INT-129', 'INT-130', 'INT-138']
        if item[0] in keys:
            workload_int_list.append(item)
            workload_filtered_list.remove(item)
    # Iterate over the list of tickets from JIRA source
    for item in workload_filtered_list:
        key = item[0]
        summary = item[1]
        for nested_item in item[4]:
            started = nested_item[0].replace(' ', 'T') + '.000-0000'
            spent = int(nested_item[1])
            issues = jira_response.search_issues('"ID client request" ~ %s' % (key), maxResults=1)
            if issues:
                for v in issues:
                    issue = v
                print('WARNING: Issue {} already exists with key {}'.format(key, issue))
            else:
                issue_dict = {
                    'project': {'key': 'EDOTRF'},
                    'summary': key + ' - ' + summary,
                    'description': 'Started: {}\nSpent: {} hours'.format(started, int(spent)/3600),
                    'issuetype': {'name': issuetype_dict[item[3]]},
                    'customfield_12072': serviceline_dict[item[3]],            # Línea de servicio
                    'customfield_12049': key                                   # ID cliente
                }
                issue = jira_response.create_issue(fields=issue_dict)
                if issue:
                    print('OK: A new ticket was created', key + ' - ' + summary)
                else:
                    print('FAILED: When trying to create the ticket:', key + ' - ' + summary)
            worklogs_kosin = jira_response.worklogs(issue)
            if check_existing_worklog(user, worklogs_kosin, started):
                # Return a message saying that the worklog already exists
                print(f'Worklog with the same date already exists. Ticket: %s, Date: %s' % (issue, started[:10]))
            else:
                url = jira_kosin_url + 'rest/api/2/issue/' + str(issue) + '/worklog'
                add_worklog(auth, url, started, spent)
    #Iterate on internal tickets
    for item in workload_int_list:
        key = key_dict.get(item[0])
        #issue = jira_response.search_issues('"ID client request" ~ %s' % (key))
        for nested_item in item[4]:
            started = nested_item[0].replace(' ', 'T') + '.000-0000'
            spent = int(nested_item[1])
            if key != None:
                worklogs_kosin = jira_response.worklogs(key)
                if check_existing_worklog(user, worklogs_kosin, started):
                    # Return a message saying that the worklog already exists
                    print(f'Worklog with the same date already exists. Ticket: %s, Date: %s' % (key, started[:10]))
                else:
                    url = jira_kosin_url + 'rest/api/2/issue/' + key + '/worklog'
                    add_worklog(auth, url, started, spent)

def add_worklog(auth, url, started, spent):
    headers = {
      "Accept": "application/json",
      "Content-Type": "application/json"
    }
    payload = json.dumps( {
      "comment": "I did some work here.",
      "started": started,
      "timeSpentSeconds": spent
    } )
    response = requests.request(
       "POST",
       url,
       data=payload,
       headers=headers,
       auth=auth
    )
    if response.status_code == 200 or response.status_code == 201:
        print(f'SUCCESS: Ticket workload was successfully uploaded to Kosin')
    else:
        print('Request failed with status code: {}'.format(response.status_code))

def http_auth(user, password):
    auth = HTTPBasicAuth(user, password)