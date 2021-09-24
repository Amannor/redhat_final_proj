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


MAX_JOBS = 4000
OUT_FILE = "all_jobs"
DATA_FOLDER = "sample_data"
DATA_FOLDER = os.path.join(DATA_FOLDER, "tests_locators_to_paths")

OWNER = "openshift"
REPO = "origin"
GITHUB_API_BASE_URL  = r'https://api.github.com'
GITHUB_API_PR_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/pulls/{pull_number}' #From: https://docs.github.com/en/rest/reference/pulls#get-a-pull-request
GITHUB_API_COMMIT_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/commits/{commit_hash}'

TST_FETCHING_BASE_URL = r"https://prow.ci.openshift.org/"
URL = 'https://prow.ci.openshift.org/job-history/gs/origin-ci-test/pr-logs/directory/pull-ci-openshift-origin-master-e2e-gcp?buildId'
DEFAULT_REQUEST_TIMEOUT_SECONDS = 1800

SET_CONTAINING_ONLY_EMPTY_STR = set()
SET_CONTAINING_ONLY_EMPTY_STR.add("")

def get_tests_locators_to_paths(artifacts_url, test_locators_set, batch_size_to_write = 30):
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} Fetching {len(test_locators_set)} test paths')
    artifacts_webpage = None
    soup = None
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
                artifacts_webpage = requests.get(artifacts_url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
            if soup is None:
                soup = BeautifulSoup(artifacts_webpage.text, 'html.parser')
            for link in soup.find_all('a'):
                h_ref_text = link.get('href')
                basename = ntpath.basename(h_ref_text)
                if basename.startswith("junit_e2e_") and basename.endswith(".xml"):  # TODO: better - check using regex if it's of the pattern: junit_e2e_XXXXXXXX-XXXXXX.xml (every X is a digit)
                    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} full url: {artifacts_url}{basename}')
                    response = requests.get(f'{artifacts_url}{basename}', timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
                    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} response size: {len(response.content)}')
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
    return tests_locators_to_paths

def write_data(ignore_previously_fetched_mappings = True):

    all_data = dict()

    r = requests.get(url=URL, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
    size = len('var allBuilds = ')
    index = r.text.find('var allBuilds = ')
    i = 0
    overall_tests_to_paths = dict()

    if ignore_previously_fetched_mappings:
        for filename in os.listdir(DATA_FOLDER):
            if filename.startswith("tests_locators_to_paths_") and filename.endswith(".json"):
                print(f'Loading existing data from: {os.path.join(DATA_FOLDER, filename)}')
                with open(os.path.join(DATA_FOLDER, filename)) as f:
                    data = json.load(f)
                for k in data.keys():
                    if len(data[k]) > 0 and set([v.replace('"', '') for v in data[k]]) != SET_CONTAINING_ONLY_EMPTY_STR:
                        overall_tests_to_paths[k] = data[k]

    while index > 0 and i < MAX_JOBS:
        cur_tests_to_paths = dict()

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
                spyglass_res = requests.get(f'{TST_FETCHING_BASE_URL}{item["SpyglassLink"]}', timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)
                if spyglass_res.status_code != 200:
                    print(f'Got {spyglass_res.status_code} response code. Skipping item')
                    continue
                close_i = spyglass_res.text.index(r'>Artifacts</a>')
                open_i = spyglass_res.text[:close_i].rfind('href=')
                artifacts_url = spyglass_res.text[open_i + len("href=") + 1:close_i-1] + r'artifacts/e2e-gcp/openshift-e2e-test/artifacts/junit/'
                artifacts_webpage = requests.get(artifacts_url, timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS)

                soup = BeautifulSoup(artifacts_webpage.text, 'html.parser')
                ci_date = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
                for link in soup.find_all('a'):
                    h_ref_text = link.get('href')
                    basename = ntpath.basename(h_ref_text)
                    if basename.startswith("e2e-intervals_") and basename.endswith(".json"): #TODO: better - check using regex if it's of the pattern: e2e-intervals_XXXX_XXXX.json (every X is a digit)
                        tests_results = requests.get(f'{artifacts_url}{basename}', timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS).json()
                        base_date = basename[len('e2e-intervals_'):len(basename) - len('.json')]
                        ci_date = datetime.datetime(int(base_date[0:4]), int(base_date[4:6]),
                                                    int(base_date[6:8]), 0, 0, 0).strftime("%Y-%m-%dT%H:%M:%S")
                        test_locators = set()
                        for tests_result in tests_results["items"]:
                            cur_locator = tests_result["locator"]
                            if (not cur_locator in overall_tests_to_paths) or len(overall_tests_to_paths[cur_locator]) == 0:
                                test_locators.add(cur_locator)


                        cur_tests_locators_to_paths = get_tests_locators_to_paths(artifacts_url, test_locators)
                        for t_key in cur_tests_locators_to_paths.keys():
                            if (not t_key in cur_tests_to_paths) or len(cur_tests_to_paths[t_key]) == 0:
                                cur_tests_to_paths[t_key] = cur_tests_locators_to_paths[t_key]

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

        if len(cur_tests_to_paths) == 0:
            print ("No records to write")
        else:
            for t_key in cur_tests_to_paths.key():
                if (not t_key in overall_tests_to_paths) or len(overall_tests_to_paths[t_key]) == 0:
                    overall_tests_to_paths[t_key] = cur_tests_to_paths[t_key]

    epoch_time = int(time.time())
    out_fname = os.path.join(DATA_FOLDER, f'{OUT_FILE}_{epoch_time}.json')
    with open(out_fname, 'w') as f_out:
        json.dump(all_data, f_out, indent=4)


if __name__ == "__main__":
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  {os.path.basename(__file__)} Start')
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    write_data()
    print(f'{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  {os.path.basename(__file__)} End')