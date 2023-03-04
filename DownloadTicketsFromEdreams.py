from functions import *

# Upload access parameters from config.ini
config_data = read_config_ini()

jira_edreams_url = config_data['JIRA Edreams url']
edreams_user = config_data['Edreams user']
edreams_password = config_data['Edreams password']

# Connect to JIRA source
jira_source = connect_to_jira(jira_edreams_url, edreams_user, edreams_password)

# Obtain the list of tickets to be processed
date_from = obtain_date_from()

# Read all tickets from a certain user defined date onwards
get_list_source(edreams_user, jira_source, date_from)

jira_source.close()
