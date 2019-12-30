import os
import yaml
import todoist
import string

import easywebdav.client

easywebdav.basestring = str
easywebdav.client.basestring = str
import easywebdav

from pprint import PrettyPrinter

pp = PrettyPrinter(indent=4)

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath

with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())

api = todoist.TodoistAPI(config['todoist_token'])
api.sync()
# pp.pprint(api.state)

# Find required project
for key, value in api.state.items():
    if key == 'projects':
        # print (value)
        for project in value:
            if project['name'] == config['todoist_project']:
                project_id = project['id']
                break

        break

items = []

for value in api.state['items']:
    if value['project_id'] == project_id:
        if config['max_items'] != 0 and len(items) > int(config['max_items']) - 1:
            break
        items.append("({}) {}".format(string.ascii_uppercase[4 - value['priority']], value['content']))

output_text = ""

for i in sorted(items):
    # print (i)
    output_text += i + "\n"

# TODO Make 'type' selection work
local_filepath = os.path.join(appdir, config['filename_output'])

with open(local_filepath, 'w+', encoding='utf-8', errors='ignore') as f:
    f.write(output_text)

webdav = easywebdav.connect(config['webdav_url'], username=config['webdav_login'], password=config['webdav_password'],
                            protocol='https', port=443, verify_ssl=False, path=config['webdav_path'])
#print(webdav.ls("/"))
webdav.upload(local_filepath, "{}/{}".format(config['webdav_directory'], config['filename_output']))
