import json
import os
from datetime import datetime, timedelta
from datetime import timedelta
import math
import random
import time


import argparse
import json
import datetime
from random import randint, sample
import requests


MAX_JOBS = 40
OUT_FILE = "all_jobs" #Old: '/Users/rarviv/Downloads/all_jobs.json'

OWNER = "openshift"
REPO = "origin"
GITHUB_API_BASE_URL  = r'https://api.github.com'
GITHUB_API_PR_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/pulls/{pull_number}'
GITHUB_API_COMMIT_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/commits/{commit_hash}'


def change_priorities(file):
    with open(file, 'r') as f_jobs:
        jobs = json.load(f_jobs)
        # jobs_list = list(filter(lambda x: '2021-08-18T' > x['metadata']['creationTimestamp'] >= '2021-08-14T', jobs['items']))
        jobs_list = list(filter(lambda x: 'refs' in x['spec'] and x['spec']['refs']['org'] == 'openshift' and x['spec']['refs']['repo'] == 'origin' and x['status']['state'] == 'failure', jobs['items']))
        print(len(jobs_list))

URL = 'https://prow.ci.openshift.org/job-history/gs/origin-ci-test/pr-logs/directory/pull-ci-openshift-origin-master-e2e-gcp?buildId'


def add_pr_details(cur_code_change, cur_pr):
    cur_code_change["user_id"] = cur_pr["user"]["id"]
    cur_code_change["user_type"] = cur_pr["user"]["type"]
    cur_code_change["is_user_admin"] = cur_pr["user"]["site_admin"]
    cur_code_change["milestone"] = cur_pr["milestone"]
    cur_code_change["mergeable"] = cur_pr["mergeable"]
    cur_code_change["rebaseable"] = cur_pr["rebaseable"]

    cur_code_change["assignees"] = list()
    for assignee in cur_pr["assignees"]:
        cur_assignee = dict()
        cur_assignee["assignee_id"] = assignee["id"]
        cur_assignee["assignee_type"] = assignee["type"]
        cur_assignee["is_assignee_admin"] = assignee["site_admin"]
        cur_code_change["assignees"].append(cur_assignee)

    cur_code_change["requested_reviewers"] = list()
    for reviewer in cur_pr["requested_reviewers"]:
        cur_reviewer = dict()
        cur_reviewer["reviewer_id"] = reviewer["id"]
        cur_reviewer["reviewer_type"] = reviewer["type"]
        cur_reviewer["is_reviewer_admin"] = reviewer["site_admin"]
        cur_code_change["requested_reviewers"].append(cur_reviewer)

    # TODO - also add requested teams?

    cur_code_change["labels"] = list()
    for label in cur_pr["labels"]:
        cur_label = dict()
        cur_label["label_id"] = label["id"]
        cur_label["label_default"] = label["default"]
        cur_code_change["labels"].append(cur_label)

    return cur_code_change


def get_data():
    all_data = dict()
    changeset_to_failed_tests = list()
    r = requests.get(url=URL)
    size = len('var allBuilds = ')
    index = r.text.find('var allBuilds = ')
    i = 0
    while index > 0 and i<MAX_JOBS:
        last_index = r.text.find(';\n</script>')
        temp = r.text[index + size:last_index]
        jobs = json.loads(temp)
        jobs_len = len(jobs)-1
        i = i+jobs_len+1
        for item in jobs:
            all_data[item['ID']] = item
            for pr_details in item['Refs']['pulls']:
                cur_code_change = dict()
                cur_pr_suffix = GITHUB_API_PR_SUFFIX_PATTERN.format(owner=OWNER, repo=REPO,
                                                                    pull_number=pr_details['number'])
                cur_pr = requests.get(f'{GITHUB_API_BASE_URL}{cur_pr_suffix}').json()
                cur_code_change = add_pr_details(cur_code_change, cur_pr)
                cur_pr_commits_details = requests.get(cur_pr['commits_url']).json()
                cur_code_change_commits = list()
                for commit_details in cur_pr_commits_details:
                    cur_commit_suffix = GITHUB_API_COMMIT_SUFFIX_PATTERN.format(owner=OWNER, repo=REPO,
                                                                                commit_hash=commit_details["sha"])
                    cur_commit = requests.get(f'{GITHUB_API_BASE_URL}{cur_commit_suffix}').json()
                    commit_obj = dict()
                    commit_obj["author_id"] = cur_commit["author"]["id"]
                    commit_obj["author_type"] = cur_commit["author"]["type"]
                    commit_obj["is_author_admin"] = cur_commit["author"]["site_admin"]
                    commit_obj["commit_files"] = list()
                    for commit_file in cur_commit["files"]:
                        file_obj = dict()
                        file_obj["filename"] = commit_file["filename"]
                        file_obj["status"] = commit_file["status"]
                        file_obj["additions"] = commit_file["additions"]
                        file_obj["deletions"] = commit_file["deletions"]
                        file_obj["changes"] = commit_file["changes"]
                        commit_obj["commit_files"].append(file_obj)
                    cur_code_change_commits.append(commit_obj)
                cur_code_change["commits"] = cur_code_change_commits
                test_info = f'test_mock_{len(changeset_to_failed_tests)}'
                changeset_to_failed_tests.append((cur_code_change, test_info))



        x = jobs[jobs_len]['ID']
        r = requests.get(url=URL+'='+x)
        size = len('var allBuilds = ')
        index = r.text.find('var allBuilds = ')
        print(i)

    epoch_time = int(time.time())
    with open(f'{OUT_FILE}_{epoch_time}.json', 'w') as f_opt:
        json.dump(all_data, f_opt, indent=4)




if __name__ == "__main__":
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_19_8_18_00.js')
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_18_8_12_00.js')
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_19_8_8_00.js')
    get_data()