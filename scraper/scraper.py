import json
import ntpath
import os
import time
import datetime
import sys

import requests
from bs4 import BeautifulSoup
import xmltodict
import re

from credentials import username
from credentials import token

MAX_JOBS = 4000
OUT_FILE = "all_jobs" #Old: '/Users/rarviv/Downloads/all_jobs.json'
DATA_FOLDER = "sample_data"

OWNER = "openshift"
REPO = "origin"
GITHUB_API_BASE_URL  = r'https://api.github.com'
GITHUB_API_PR_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/pulls/{pull_number}' #From: https://docs.github.com/en/rest/reference/pulls#get-a-pull-request
GITHUB_API_COMMIT_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/commits/{commit_hash}'

TST_FETCHING_BASE_URL = r"https://prow.ci.openshift.org/"

DEFAULT_REQUEST_TIMEOUT_SECONDS = 1800

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


def get_cur_change_commits_details(commits_url):
    cur_pr_commits_details = fetch_url_and_sleep_if_needed(commits_url)
    cur_code_change_commits = list()
    for commit_details in cur_pr_commits_details:
        cur_commit_suffix = GITHUB_API_COMMIT_SUFFIX_PATTERN.format(owner=OWNER, repo=REPO,
                                                                    commit_hash=commit_details["sha"])
        cur_commit = fetch_url_and_sleep_if_needed(f'{GITHUB_API_BASE_URL}{cur_commit_suffix}')

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
    return cur_code_change_commits


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


def get_failed_tests_locators_to_paths(artifacts_url, failed_test_locators):
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Fetching failed test paths')
    artifacts_webpage = None
    soup = None
    failed_tests_locators_to_paths = dict()

    for failed_test_locator in failed_test_locators:
        tests_paths = set()
        open_i = failed_test_locator.find("[")
        close_i = failed_test_locator.rfind("]")
        if open_i<0 or close_i<0:
            print(f'No valid failed test string found for {failed_test_locator} - unable tp deduce path')
            failed_tests_locators_to_paths[failed_test_locator] = [""]
            continue

        failed_test_id = failed_test_locator[open_i:close_i+1]
        if artifacts_webpage is None:
            artifacts_webpage = requests.get(artifacts_url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
        if soup is None:
            soup = BeautifulSoup(artifacts_webpage.text, 'html.parser')
        for link in soup.find_all('a'):
            h_ref_text = link.get('href')
            basename = ntpath.basename(h_ref_text)
            if basename.startswith("junit_e2e_") and basename.endswith(".xml"):  # TODO: better - check using regex if it's of the pattern: junit_e2e_XXXXXXXX-XXXXXX.xml (every X is a digit)
                response = requests.get(f'{artifacts_url}{basename}', timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
                dict_data = xmltodict.parse(response.content) #From https://stackoverflow.com/a/67296064
                if not ('testsuite' in dict_data and 'testcase' in dict_data['testsuite']):
                    continue
                test_general_info_list = [t for t in dict_data['testsuite']['testcase'] if t["@name"] == failed_test_id]

                #Option 1 - looking in failure texts
                test_fail_info_list = [t for t in test_general_info_list if "failure" in t and '#text' in t["failure"]]
                for test_fail_info in test_fail_info_list:
                    path_start_i = test_fail_info["failure"]['#text'].find(f'github.com/{OWNER}/{REPO}')
                    if path_start_i <0:
                        continue
                    partial_s = test_fail_info["failure"]['#text'][path_start_i:]
                    colon_i = partial_s.find(":")
                    sqr_i = partial_s.find("]")
                    if colon_i < 0:
                        path_end_i = sqr_i
                    elif sqr_i < 0:
                        path_end_i = colon_i
                    else:
                        path_end_i = min(sqr_i, colon_i)
                    path_end_i += path_start_i
                    test_path = test_fail_info["failure"]['#text'][path_start_i:path_end_i]
                    test_path = re.sub('\s+', ' ', test_path)  # Removing leading \ trailing whitespaces
                    tests_paths.add(test_path)

                # Option 2 - looking in the system out prints
                if len(tests_paths) == 0:
                    test_fail_info_list = [t for t in test_general_info_list if "system-out" in t]
                    for test_fail_info in test_fail_info_list:
                        path_start_i = test_fail_info["system-out"].find(f'github.com/{OWNER}/{REPO}')
                        if path_start_i < 0:
                            continue
                        partial_s = test_fail_info["system-out"][path_start_i:]
                        colon_i = partial_s.find(":")
                        sqr_i = partial_s.find("]")
                        if colon_i < 0:
                            path_end_i = sqr_i
                        elif sqr_i < 0:
                            path_end_i = colon_i
                        else:
                            path_end_i = min(sqr_i, colon_i)
                        path_end_i += path_start_i
                        test_path = test_fail_info["system-out"][path_start_i:path_end_i]
                        test_path = re.sub('\s+', ' ', test_path) #Removing leading \ trailing whitespaces
                        tests_paths.add(test_path)

        failed_tests_locators_to_paths[failed_test_locator] = list(tests_paths)

    if len(failed_tests_locators_to_paths) == 0:
        print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} No tests paths found')
    return failed_tests_locators_to_paths

def get_data(should_include_commits = True):
    all_data = dict()

    r = requests.get(url=URL, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
    size = len('var allBuilds = ')
    index = r.text.find('var allBuilds = ')
    i = 0
    while index > 0 and i<MAX_JOBS:
        changeset_to_failed_tests = list()
        last_index = r.text.find(';\n</script>')
        if last_index < 0:
            print(f'last_index {last_index} - skipping this iteration')
            index = r.text.find('var allBuilds = ')
        temp = r.text[index + size:last_index]
        jobs = json.loads(temp)
        if len(jobs) == 0:
            print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Found no jobs, skipping')
        jobs_len = len(jobs)-1
        i = i+jobs_len+1
        print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Got {len(jobs)} items')
        for item in jobs:
            try:
                print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Item id: {item["ID"]}')
                all_data[item['ID']] = item

                #Test fetching
                print("Fetching tests")
                cur_tests_count = 0
                spyglass_res = requests.get(f'{TST_FETCHING_BASE_URL}{item["SpyglassLink"]}', timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
                if spyglass_res.status_code != 200:
                    print(f'Got {spyglass_res.status_code} response code. Skipping item')
                    continue
                close_i = spyglass_res.text.index(r'>Artifacts</a>')
                open_i = spyglass_res.text[:close_i].rfind('href=')
                artifacts_url = spyglass_res.text[open_i + len("href=") + 1:close_i-1] + r'artifacts/e2e-gcp/openshift-e2e-test/artifacts/junit/'
                artifacts_webpage = requests.get(artifacts_url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)

                soup = BeautifulSoup(artifacts_webpage.text, 'html.parser')
                failed_tests_info = list()
                ci_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                for link in soup.find_all('a'):
                    h_ref_text = link.get('href')
                    basename = ntpath.basename(h_ref_text)
                    if basename.startswith("e2e-intervals_") and basename.endswith(".json"): #TODO: better - check using regex if it's of the pattern: e2e-intervals_XXXX_XXXX.json (every X is a digit)
                        tests_results = requests.get(f'{artifacts_url}{basename}', timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).json()
                        cur_tests_count = len(tests_results["items"])
                        base_date = basename[len('e2e-intervals_'):len(basename) - len('.json')]
                        ci_date = datetime.datetime(int(base_date[0:4]), int(base_date[4:6]),
                                                    int(base_date[6:8]), 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%S")
                        failed_test_locators = list()
                        for tests_result in tests_results["items"]:
                            if tests_result["message"].endswith("\"Failed\""):
                                failed_test_locators.append(tests_result["locator"])

                        failed_tests_locators_to_paths = get_failed_tests_locators_to_paths(artifacts_url, failed_test_locators)
                        failed_tests_info.append(failed_tests_locators_to_paths)

                if len(failed_tests_info) == 0:
                    print("No failed tests found - skipping this item")
                    continue


                # Code-change fetching
                print("Fetching code-change")
                for pr_details in item['Refs']['pulls']:
                    cur_code_change = dict()
                    cur_code_change["target_cardinality"] = cur_tests_count
                    cur_pr_suffix = GITHUB_API_PR_SUFFIX_PATTERN.format(owner=OWNER, repo=REPO,
                                                                        pull_number=pr_details['number'])

                    cur_pr = fetch_url_and_sleep_if_needed(f'{GITHUB_API_BASE_URL}{cur_pr_suffix}')

                    cur_code_change = add_pr_details(cur_code_change, cur_pr)
                    if should_include_commits:
                        cur_code_change["commits"] = get_cur_change_commits_details(cur_pr['commits_url'])
                    else:
                        pr_files = list()
                        cur_pr_files = fetch_url_and_sleep_if_needed(f'{GITHUB_API_BASE_URL}{cur_pr_suffix}/files')
                        for cur_pr_file in cur_pr_files:
                            pr_file_to_add  = dict()
                            pr_file_to_add["filename"] = cur_pr_file["filename"]
                            pr_file_to_add["status"] = cur_pr_file["status"]
                            pr_file_to_add["additions"] = cur_pr_file["additions"]
                            pr_file_to_add["deletions"] = cur_pr_file["deletions"]
                            pr_file_to_add["changes"] = cur_pr_file["changes"]
                            pr_files.append(pr_file_to_add)
                        cur_code_change["files"] = pr_files
                    cur_data = {"code_changes_data": cur_code_change, "failed_tests": failed_tests_info, "date": ci_date, "artifact_url": artifacts_url}
                    changeset_to_failed_tests.append(cur_data)
            except:
                print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Error: type {sys.exc_info()[0]}\nvalue {sys.exc_info()[1]}\ntraceback {sys.exc_info()[2]}', ) #See https://docs.python.org/3/library/sys.html#sys.exc_info

        try:
            x = jobs[jobs_len]['ID']
            print(f'x {x}')
            r = requests.get(url=URL+'='+x, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
            size = len('var allBuilds = ')
            index = r.text.find('var allBuilds = ')
        except:
            print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Error: type {sys.exc_info()[0]}\nvalue {sys.exc_info()[1]}\ntraceback {sys.exc_info()[2]}', )  # See https://docs.python.org/3/library/sys.html#sys.exc_info
            print(f'jobs_len {jobs_len}')

        print(i)

        if len(changeset_to_failed_tests) == 0:
            print ("No records to write")
        else:
            epoch_time = int(time.time())
            out_fname = f'changeset_to_failed_tests_{epoch_time}.json'
            out_fname = os.path.join(DATA_FOLDER, out_fname)
            print(f'Writing to file {out_fname} (num of tuples: {len(changeset_to_failed_tests)})')
            with open(out_fname, 'w') as f_out:
                json.dump(changeset_to_failed_tests, f_out, indent=4)

    epoch_time = int(time.time())
    out_fname = os.path.join(DATA_FOLDER, f'{OUT_FILE}_{epoch_time}.json')
    with open(out_fname, 'w') as f_out:
        json.dump(all_data, f_out, indent=4)







if __name__ == "__main__":
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_19_8_18_00.js')
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_18_8_12_00.js')
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_19_8_8_00.js')
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} {os.path.basename(__file__)} Start')
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    get_data()
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  {os.path.basename(__file__)} End')
