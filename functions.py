#/usr/bin/python3
"""
Ich hab die Datei angelegt um erstmal ein paar funktionen an sich zu testen.
Aber da du ja gerne einige funktionen auslagern wolltest, könenn dir dann auch
hier rein so nach und nach (Handler functions würd ich im mens_bot.py lassen)
"""

import requests
import configparser

def createIssue(title, msg):
    """
    Erstellt ein Issue zu unserem GitHub-Repo.
    :param title: Issue Titel
    :param msg: Issue Inhalt (markdown ok)
    """
    cp = configparser.ConfigParser()
    cp.read('private.ini')

    login = cp.get('private', 'gh_user')
    pw = cp.get('private', 'gh_pw')
    s = requests.session()
    s.auth = (login, pw)
    url_api = 'https://api.github.com/repos/telebotter/mensabot/issues'
    issue = {'title': title, 'body': msg, 'labels': ['user request']}
    s.post(url_api, json=issue)