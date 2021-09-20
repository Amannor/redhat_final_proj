import datetime
import json
import os
import time

import requests

from credentials import username
from credentials import token

OWNER = "openshift"
REPO = "origin"
GITHUB_API_BASE_URL  = r'https://api.github.com'
GITHUB_API_FILE_COMMITS_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/commits?path={PATH_TO_FILE}'
GITHUB_API_TREE_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/git/trees/{tree_sha}' #From https://docs.github.com/en/rest/reference/git#trees
DATA_FOLDER = 'sample_data'
DATA_FOLDER = os.path.join(DATA_FOLDER, "files_changes_history")
ALL_PROJ_FILES_FILE = 'all_project_files_metdata.json'
PROJ_ROOT_SHA = r'507b91e30606df94166e3a13a02b046222abbc8f' #Taken from https://api.github.com/repos/openshift/origin/branches/master (see https://stackoverflow.com/a/25128301)
MAX_RECORDS_PER_FILE = 300
DEFAULT_REQUEST_TIMEOUT_SECONDS = 1800


def fetch_url_and_sleep_if_needed(url, use_auth=True):
    url_data = requests.get(url, auth=(username, token), timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).json() if use_auth else requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).json()
    if "message" in url_data and 'API rate limit exceeded' in url_data["message"]:
        print(url_data["message"])
        print(url_data["documentation_url"])
        e = datetime.datetime.now()
        print(f'Current time: {e.strftime("%Y-%m-%d %H:%M:%S")}')
        print("Going to sleep for an hour")
        time.sleep(60 * 60)
        e = datetime.datetime.now()
        print(f'Current time: {e.strftime("%Y-%m-%d %H:%M:%S")}')
        print("Woke up! Continuing where I left off")
        url_data = requests.get(url, auth=(username, token), timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).json() if use_auth else requests.get(url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).json()

    return url_data


def fill_projects_data_file_if_not_exist():
    if not os.path.exists(ALL_PROJ_FILES_FILE):
        suffix = GITHUB_API_TREE_SUFFIX_PATTERN.format(owner=OWNER, repo=REPO, tree_sha=PROJ_ROOT_SHA)
        suffix += r'?recursive = 1'
        full_url = f'{GITHUB_API_BASE_URL}{suffix}' # https://api.github.com/repos/openshift/origin/git/trees/507b91e30606df94166e3a13a02b046222abbc8f?recursive=1'

        all_files_data = fetch_url_and_sleep_if_needed(full_url)
        with open(ALL_PROJ_FILES_FILE, 'w') as f_out:
            json.dump(all_files_data, f_out, indent=4)


def get_data():
    fill_projects_data_file_if_not_exist()

    with open(ALL_PROJ_FILES_FILE) as f:
        all_files_data = json.load(f)
        files_changes_history = list()
        total_files_count = len(all_files_data['tree'])
        file_counter = 0
        for file_data in all_files_data['tree']:
            path = file_data['path']
            file_counter+=1

            print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ({file_counter}/{total_files_count}) {path}')

            suffix = GITHUB_API_FILE_COMMITS_SUFFIX_PATTERN.format(owner=OWNER, repo=REPO, PATH_TO_FILE=path)
            full_url = f'{GITHUB_API_BASE_URL}{suffix}'
            file_commit_history = fetch_url_and_sleep_if_needed(full_url)
            cur_file_changes_history = dict()
            cur_file_changes_history['path'] = path
            file_commits = list()
            for file_commit_record in file_commit_history:
                file_commit = dict()
                file_commit["authored"] = file_commit_record["commit"]["author"]["date"]
                file_commit["committed"] = file_commit_record["commit"]["committer"]["date"]
                file_commit['commit_sha'] = file_commit_record["sha"]
                file_commits.append(file_commit)
            cur_file_changes_history["commits"] = file_commits
            files_changes_history.append(cur_file_changes_history)
            if len(files_changes_history) == MAX_RECORDS_PER_FILE:
                epoch_time = int(time.time())
                out_fname = f'files_changes_history_{epoch_time}.json'
                out_fname = os.path.join(DATA_FOLDER, out_fname)
                print(f'Writing to file {out_fname} (num of tuples: {len(files_changes_history)})')
                with open(out_fname, 'w') as f_out:
                    json.dump(files_changes_history, f_out, indent=4)
                files_changes_history = list()

        epoch_time = int(time.time())
        out_fname = f'files_changes_history_{epoch_time}.json'
        out_fname = os.path.join(DATA_FOLDER, out_fname)
        print(f'Writing to file {out_fname} (num of tuples: {len(files_changes_history)})')
        with open(out_fname, 'w') as f_out:
            json.dump(files_changes_history, f_out, indent=4)

if __name__ == "__main__":
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {os.path.basename(__file__)} Start')

    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    get_data()

    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {os.path.basename(__file__)} End')




