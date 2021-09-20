import os
from requests.models import Response
import yaml
import json
import requests
import todoist
import string
import tempfile
import sys
# easywebdav python3 hack
import easywebdav.client
from datetime import date, datetime, timezone
from dateutil.parser import parse
import humanize
import re

import pprint

easywebdav.basestring = str
easywebdav.client.basestring = str

import easywebdav

appdir = os.path.dirname(os.path.realpath(__file__))  # rp, realpath
datadir = os.path.join(appdir, "data")

if not os.path.exists(datadir):
    os.makedirs(datadir)

# Read config
with open(os.path.join(appdir, 'config.yaml'), 'r') as f:
    config = yaml.load(f.read())

# Fetch todoist items
api = todoist.TodoistAPI(config['todoist_token'])
api.sync()

if config['debug']:
    with open(os.path.join(appdir, "debug.json"), "w+", encoding="utf-8") as f:
        f.write(pprint.pformat(api.state, indent=4))


def debug(text):
    if config['debug']:
        print(text)


# json.dumps(api.state, default=lambda o: '<not serializable>', indent=4)
# Pprint for debug purposes
# from pprint import PrettyPrinter
# pp = PrettyPrinter(indent=4, width=10000)
# pp.pprint(api.state)
# input()

today_path = os.path.join(datadir, datetime.now().strftime("%Y_%m_%d") + ".mem")

if not os.path.exists(today_path):
    with open(today_path, "w+", encoding="utf-8") as f:
        f.write("")


def today_memory():
    with open(today_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines


def remember_task(task):
    lines = today_memory()
    if task not in lines:
        with open(today_path, "a+", encoding="utf-8") as f:
            f.write(task + "\n")
        print(f"Task '{task}' added to memory for today. ({lines})")
    else:
        print(f"Task '{task}' already remembered as completed for today.")


def completed_today():
    with open(today_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    tasks = 0
    for line in lines:
        if line.strip():
            tasks += 1
    return tasks

def tz_aware(dt):
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None

def get_project_id(name, type='project'):
    project_id = None
    if type != 'filter' and name != 'Inbox':
        name = name[1:]
    # Find required project
    for key, value in api.state.items():
        if key == (type + 's'):
            # print (value)
            for project in value:
                if project['name'] == name:
                    project_id = project['id']
                    break
            break
    return project_id

def project_type_from_name(name):
    if name.startswith('#'):
        return 'project'
    elif name.startswith('@'):
        return 'label'
    elif name.startswith('!f'):
        return 'filter'
    else:
        return 'project'

def get_project_items(project_name):
    # Filter items
    # Filter completed out
    project_type = project_type_from_name(project_name)
    project_id = get_project_id(project_name, project_type)
    items = []
    for item in api.state['items']:
        select = False
        if project_name == "Today":
            if item['due'] != None:
                due_date = parse(item['due']['date'])
                due_date = due_date.date()
                now_date = date.today()
                date_check = due_date <= now_date
                # debug(f"Check due date: {due_date} <= {now_date} = {date_check};")
                if date_check:
                    select = True

        elif project_type == 'project' and item['project_id'] == project_id:
            select = True
        elif project_type == 'label' and project_id in item['labels']:
            select = True

        if select:
            if config['max_items'] != 0 and len(items) > int(config['max_items']) - 1:
                break
            process_item_for_items(item, items)
    return items

def get_filter_items(filter_query):
    if filter_query.startswith('!f '):
        filter_query = filter_query[2:] 
    response = requests.get(
        "https://api.todoist.com/rest/v1/tasks",
        params={
            "filter": filter_query
        },
        headers={
            "Authorization": "Bearer %s" % config['todoist_token']
        }).json()
    max_items = config['max_items']
    if max_items != 0:
        response = response[:max_items]
    items = []
    for item in response:
        process_item_for_items(item, items)
    return items

def process_item_for_items(item, items):
    now = datetime.now()
    if type(item) is todoist.models.Item:
        checked = item['checked']
        due = item['due']
    else:
        checked = item['completed']
        due = item.get('due', None)
    if checked == 0:
        item_text = "({}) {}".format(string.ascii_uppercase[4 - item['priority']], item['content'])
        if config['show_due_date'] and due != None:
            due_date = parse(due['date'], ignoretz=True)
            time_ago = ("Today " +
                        re.sub('0(\d:)', r'\1', due_date.strftime('%I:%M%p')) if due_date.date() == date.today()
                            else humanize.naturaltime(now - due_date))
            item_text = f"{item_text} | due: {time_ago}"
        items.append(item_text)
    elif checked == 1:
        remember_task(item['content'])
        if config['show_completed_tasks']:
            items.append("x ({}) {}".format(string.ascii_uppercase[4 - item['priority']], item['content']))
        if config['clean_up_completed_tasks']:
            print(f"Deleting task '{item['content']}'")
            task = api.items.get_by_id(item['id'])
            task.delete()
            api.commit()
    else:
        print("Something's not right, did Todoist change API? item['checked'] is not 0 or 1.")

def text_from_items(projects_items, filter_out=[], hide_low_priority=False):
    # Create output text
    output_text = ""
    for project, items in projects_items.items():
        output_text += project + ":\n\n"
        if len(items) == 0:
            output_text += "Nothing To Do 😄\n"
        for i in sorted(items):
            if (i in filter_out) or (hide_low_priority and "(D) " in i):
                continue 
            output_text += i + "\n"
        output_text += "\n"
    return output_text


def generate_output_text():
    project_name = config['todoist_project']
    project_items = {}
    for name in [x.strip() for x in project_name.split(',')]:
        project_type = project_type_from_name(name)
        if project_type == 'filter':
            project_items[name] = get_filter_items(name)
        else:
            debug(name)
            project_items[name] = get_project_items(name)
    return text_from_items(project_items)

if __name__ == "__main__":
    # TODO Make 'type' selection work

    local_filepath = os.path.join(appdir, config['filename_output'])

    output_text = generate_output_text()

    debug(output_text)

    # Copy if copy
    if config['export_file_as']:
        if os.path.exists(config['export_file_as']):
            with open(config['export_file_as'], 'r', encoding='utf-8', errors='ignore') as f:
                old_text = f.read()
            if output_text == old_text:
                print("No changes in todo list. Exit.")
                sys.exit()
        with open(config['export_file_as'], 'w+', encoding='utf-8', errors='ignore') as f:
            f.write(output_text)

    # Upload to webdav
    # if config['webdav_url']:
    #     webdav = easywebdav.connect(config['webdav_url'], username=config['webdav_login'],
    #                                 password=config['webdav_password'],
    #                                 protocol='https', port=443, verify_ssl=False, path=config['webdav_path'])

    #     with tempfile.NamedTemporaryFile(mode="wb+", delete=False) as tmp:
    #         webdav.download("{}/{}".format(config['webdav_directory'], config['filename_output']), tmp)
    #         tmp_fp = tmp.name

    #     with open(tmp_fp, "r", encoding="utf-8") as f:
    #         old_text = f.read()

    #     if output_text == old_text:
    #         print("No changes in todo list. Exit.")
    #         os.remove(tmp_fp)
    #         sys.exit()

    #     with tempfile.NamedTemporaryFile(mode="w+", encoding='utf-8', delete=False) as tmp:
    #         tmp.write(output_text)
    #         tmp_fp = tmp.name

    #     webdav.upload(tmp_fp, "{}/{}".format(config['webdav_directory'], config['filename_output']))
    #     os.remove(tmp_fp)
