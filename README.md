# TodoistToTxt

 A python script that exports your todoist tasks to txt file, formatted according to todo.txt spec.
 Supports caldav export.
 
## Requirements
- git
- python3
- pip3 (python3-pip)

Copy paste on debian systems to install requirements (remove sudo if on default debian, use with sudo on ubuntu and debian derivatives):

```
sudo apt install git python3-pip
```
 
## Installation 
 
- Clone repo anywhere you like
- Copy example_config.yaml into config.yaml and adjust settings
- todoist token is available in the web app, under preferences - integrations, API token
- Use cronjob or Task Scheduler to run this script as often as you like


# Todo

- Currently it can only publish to webdav and into a file that's located in the same folder as the script. Improve to support custom txt location on the filesystem, as well as more cloud providers.
- From todo.txt spec it currently only supports priority, which should be improved
- Ability to create custom export templates (Jinja2? Or just format)
