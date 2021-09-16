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
URL = 'https://prow.ci.openshift.org/job-history/gs/origin-ci-test/pr-logs/directory/pull-ci-openshift-origin-master-e2e-gcp?buildId'

def get_tests_locators_to_paths(artifacts_url, test_locators_set, batch_size_to_write = 30):
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Fetching {len(test_locators_set)} test paths')
    artifacts_webpage = None
    soup = None
    # failed_tests_locators_to_paths = dict()
    tests_locators_to_paths = dict()
    iteration_num = 0
    cur_batch = dict()

    for test_locator in test_locators_set:
        try:
            iteration_num += 1

            print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ({iteration_num}/{len(test_locators_set)}) {test_locator}')
            tests_paths = set()
            open_i = test_locator.find("[")
            close_i = test_locator.rfind("]")
            if open_i < 0 or close_i < 0:
                print(f'No valid failed test string found for {test_locator} - unable tp deduce path')
                cur_batch[test_locator] = [""]
                continue

            test_id = test_locator[open_i:close_i + 1]
            if artifacts_webpage is None:
                artifacts_webpage = requests.get(artifacts_url)
            if soup is None:
                soup = BeautifulSoup(artifacts_webpage.text, 'html.parser')
            for link in soup.find_all('a'):
                h_ref_text = link.get('href')
                basename = ntpath.basename(h_ref_text)
                if basename.startswith("junit_e2e_") and basename.endswith(".xml"):  # TODO: better - check using regex if it's of the pattern: junit_e2e_XXXXXXXX-XXXXXX.xml (every X is a digit)
                    response = requests.get(f'{artifacts_url}{basename}')
                    dict_data = xmltodict.parse(response.content) #From https://stackoverflow.com/a/67296064
                    if not ('testsuite' in dict_data and 'testcase' in dict_data['testsuite']):
                        continue
                    test_general_info_list = [t for t in dict_data['testsuite']['testcase'] if t["@name"] == test_id]

                    #Option 1 - looking in the system out prints
                    test_info_list = [t for t in test_general_info_list if "system-out" in t]
                    for test_info_item in test_info_list:
                        path_start_i = test_info_item["system-out"].find(f'github.com/{OWNER}/{REPO}')
                        if path_start_i < 0:
                            continue
                        partial_s = test_info_item["system-out"][path_start_i:]
                        colon_i = partial_s.find(":")
                        sqr_i = partial_s.find("]")
                        if colon_i < 0:
                            path_end_i = sqr_i
                        elif sqr_i < 0:
                            path_end_i = colon_i
                        else:
                            path_end_i = min(sqr_i, colon_i)
                        path_end_i += path_start_i
                        test_path = test_info_item["system-out"][path_start_i:path_end_i]
                        test_path = re.sub('\s+', ' ', test_path)  # Removing leading \ trailing whitespaces
                        tests_paths.add(test_path)

                    # Option 2 - looking in failure texts
                    if len(tests_paths) == 0:
                        test_info_list = [t for t in test_general_info_list if "failure" in t and '#text' in t["failure"]]
                        for test_fail_info in test_info_list:
                            path_start_i = test_fail_info["failure"]['#text'].find(f'github.com/{OWNER}/{REPO}')
                            if path_start_i < 0:
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

            # failed_tests_locators_to_paths[test_locator] = list(tests_paths)
            cur_batch[test_locator] = list(tests_paths)
            if len(cur_batch) >= batch_size_to_write:
                epoch_time = int(time.time())
                out_fname = f'tests_locators_to_paths_{epoch_time}.json'
                out_fname = os.path.join(DATA_FOLDER, out_fname)
                print(f'Writing to file {out_fname} (num of records: {len(cur_batch)})')
                with open(out_fname, 'w') as f_out:
                    json.dump(cur_batch, f_out, indent=4)
                tests_locators_to_paths.update(cur_batch)
                cur_batch = dict()
        except:
            print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Error (Iteration no. {iteration_num}): type {sys.exc_info()[0]}\nvalue {sys.exc_info()[1]}\ntraceback {sys.exc_info()[2]}', )  # See https://docs.python.org/3/library/sys.html#sys.exc_info

    if len(cur_batch) > 0:
        epoch_time = int(time.time())
        out_fname = f'tests_locators_to_paths_{epoch_time}.json'
        out_fname = os.path.join(DATA_FOLDER, out_fname)
        print(f'Writing to file {out_fname} (num of records: {len(cur_batch)})')
        with open(out_fname, 'w') as f_out:
            json.dump(cur_batch, f_out, indent=4)
        tests_locators_to_paths.update(cur_batch)

    if len(tests_locators_to_paths) == 0:
        print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} No tests paths found')
    # return failed_tests_locators_to_paths
    return tests_locators_to_paths


def write_data():
    all_data = dict()

    r = requests.get(url=URL)
    size = len('var allBuilds = ')
    index = r.text.find('var allBuilds = ')
    i = 0
    overall_tests_to_paths = dict()
    while index > 0 and i < MAX_JOBS:
        cur_tests_to_paths = dict()
        # changeset_to_failed_tests = list()
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
                # cur_tests_count = 0
                spyglass_res = requests.get(f'{TST_FETCHING_BASE_URL}{item["SpyglassLink"]}')
                if spyglass_res.status_code != 200:
                    print(f'Got {spyglass_res.status_code} response code. Skipping item')
                    continue
                close_i = spyglass_res.text.index(r'>Artifacts</a>')
                open_i = spyglass_res.text[:close_i].rfind('href=')
                artifacts_url = spyglass_res.text[open_i + len("href=") + 1:close_i-1] + r'artifacts/e2e-gcp/openshift-e2e-test/artifacts/junit/'
                artifacts_webpage = requests.get(artifacts_url)

                soup = BeautifulSoup(artifacts_webpage.text, 'html.parser')
                # failed_tests_info = list()
                ci_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                for link in soup.find_all('a'):
                    h_ref_text = link.get('href')
                    basename = ntpath.basename(h_ref_text)
                    if basename.startswith("e2e-intervals_") and basename.endswith(".json"): #TODO: better - check using regex if it's of the pattern: e2e-intervals_XXXX_XXXX.json (every X is a digit)
                        tests_results = requests.get(f'{artifacts_url}{basename}').json()
                        # cur_tests_count = len(tests_results["items"])
                        base_date = basename[len('e2e-intervals_'):len(basename) - len('.json')]
                        ci_date = datetime.datetime(int(base_date[0:4]), int(base_date[4:6]),
                                                    int(base_date[6:8]), 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%S")
                        # failed_test_locators = list()
                        test_locators = set()
                        for tests_result in tests_results["items"]:
                            cur_locator = tests_result["locator"]
                            if (not cur_locator in overall_tests_to_paths) or len(overall_tests_to_paths[cur_locator])==0:
                                test_locators.add(cur_locator)
                            # if tests_result["message"].endswith("\"Failed\""):
                            #     failed_test_locators.append(tests_result["locator"])

                        # failed_tests_locators_to_paths = get_failed_tests_locators_to_paths(artifacts_url, failed_test_locators)
                        cur_tests_locators_to_paths = get_tests_locators_to_paths(artifacts_url, test_locators)
                        for t_key in cur_tests_locators_to_paths.keys():
                            if (not t_key in cur_tests_to_paths) or len(cur_tests_to_paths[t_key]) == 0:
                                cur_tests_to_paths[t_key] = cur_tests_locators_to_paths[t_key]

                        # no_paths_found = True
                        # for key in failed_tests_locators_to_paths.keys():
                        #     if set(failed_tests_locators_to_paths[key]) != set(""):
                        #         no_paths_found = False
                        #         break
                        # if len(failed_tests_locators_to_paths>0) and not no_paths_found:
                        #     failed_tests_info.append(failed_tests_locators_to_paths)

                # if len(failed_tests_info) == 0:
                #     print("No failed tests found - skipping this item")
                #     continue


                '''
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
                    '''
            except:
                print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Error: type {sys.exc_info()[0]}\nvalue {sys.exc_info()[1]}\ntraceback {sys.exc_info()[2]}', ) #See https://docs.python.org/3/library/sys.html#sys.exc_info

        try:
            x = jobs[jobs_len]['ID']
            print(f'x {x}')
            r = requests.get(url=URL+'='+x)
            size = len('var allBuilds = ')
            index = r.text.find('var allBuilds = ')
        except:
            print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Error: type {sys.exc_info()[0]}\nvalue {sys.exc_info()[1]}\ntraceback {sys.exc_info()[2]}', )  # See https://docs.python.org/3/library/sys.html#sys.exc_info
            print(f'jobs_len {jobs_len}')

        print(i)

        if len(cur_tests_to_paths) == 0:
            print ("No records to write")
        else:
            # epoch_time = int(time.time())
            # out_fname = f'tests_to_paths_{epoch_time}.json'
            # out_fname = os.path.join(DATA_FOLDER, out_fname)
            # print(f'Writing to file {out_fname} (num of records: {len(cur_tests_to_paths)})')
            # with open(out_fname, 'w') as f_out:
            #     json.dump(cur_tests_to_paths, f_out, indent=4)
            for t_key in cur_tests_to_paths.key():
                if (not t_key in overall_tests_to_paths) or len(overall_tests_to_paths[t_key]) == 0:
                    overall_tests_to_paths[t_key] = cur_tests_to_paths[t_key]


    epoch_time = int(time.time())
    out_fname = os.path.join(DATA_FOLDER, f'{OUT_FILE}_{epoch_time}.json')
    with open(out_fname, 'w') as f_out:
        json.dump(all_data, f_out, indent=4)


if __name__ == "__main__":
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Start')
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    write_data()
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} End')