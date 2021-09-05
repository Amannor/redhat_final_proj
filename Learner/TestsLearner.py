# First XGBoost model
from numpy import loadtxt
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import os
import csv
import json

from datetime import datetime
from datetime import timedelta


def create_csv():
    path = r'flatten_data.json'

    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        fieldnames = schema["schema_fields"].keys()

    with open(r'prs.csv', mode='w') as csv_file:
        # fieldnames = ['file_name', 'num_files_changed', 'file_extension', 'num_target_tests', 'number_changes_3d',
        #               'number_changes_14d', 'number_changes_56d', 'distance', 'failed_7d', 'failed_14d',
        #               'failed_28d', 'failed_56d', 'minimal_distance', 'test_name']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        with open(path, 'r') as f_reader:
            reader = json.load(f_reader)
            for item in reader:
                writer.writerow(item)
                # f_size = len(item['code_changes_data']['files'])
                # for fn in item['code_changes_data']['files']:
                #     ext = fn['filename'].rfind('.')
                #     t_size = len(item['failed_tests'])
                #     for t in item['failed_tests']:
                #         writer.writerow({'file_name': fn['filename'], 'num_files_changed': f_size,
                #                          'file_extension': fn['filename'][ext +1:len(fn['filename'])],
                #                          'num_target_tests': t_size, 'number_changes_3d': 0,
                #         'number_changes_14d': 0, 'number_changes_56d': 0, 'distance': 0,
                #         'failed_7d': 0, 'failed_14d': 0,
                #         'failed_28d': 0, 'failed_56d': 0, 'minimal_distance': 0, 'test_name': t})


def collect_data_history():
    path_all_files = r'../scraper/all_project_files_metdata.json'
    with open(path_all_files, 'r') as f_reader:
        reader = json.load(f_reader)
        return reader


def flatten_jsons():
    path = r'../scraper/sample_data'
    history = collect_data_history()
    changed_files = []
    failed_test_files = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            if file.startswith('files_changes_history'):
                changed_files.append(os.path.join(r, file))
            elif file.startswith('changeset_to_failed_test'):
                failed_test_files.append(os.path.join(r, file))
    file_changes = commits_breakdown(changed_files)
    failure_breakdown = test_failure_breakdown(failed_test_files)

    flat_json_list = list()
    for f in failed_test_files:
        with open(f, 'r') as f_reader:
            reader = json.load(f_reader)
            for item in reader:
                f_size = len(item['code_changes_data']['commits'][0]['commit_files'])
                as_size = len(item['code_changes_data']['assignees'])
                for fn in item['code_changes_data']['commits'][0]['commit_files']:
                    ext = fn['filename'].rfind('.')
                    t_size = len(item['failed_tests'])
                    for t in item['failed_tests']:
                        flat_json = dict()
                        flat_json['file_name'] = fn['filename']
                        flat_json['num_files_changed'] = f_size
                        flat_json['file_extension'] = fn['filename'][ext + 1:len(fn['filename'])]
                        flat_json['num_target_tests'] = t_size
                        if fn['filename'] in file_changes:
                            flat_json['number_changes_3d'] = file_changes[fn['filename']][0]
                            flat_json['number_changes_14d'] = file_changes[fn['filename']][1]
                            flat_json['number_changes_56d'] = file_changes[fn['filename']][2]
                        else:
                            flat_json['number_changes_3d'] = 0
                            flat_json['number_changes_14d'] = 0
                            flat_json['number_changes_56d'] = 0
                        flat_json['project_name'] = 'NA'
                        flat_json['distinct_authors'] = as_size
                        flat_json['failed_7d'] = failure_breakdown[t][0]
                        flat_json['failed_14d'] = failure_breakdown[t][1]
                        flat_json['failed_28d'] = failure_breakdown[t][2]
                        flat_json['failed_56d'] = failure_breakdown[t][3]
                        flat_json['minimal_distance'] = 0
                        flat_json['common_tokens'] = 0
                        flat_json['test_name'] = t[len('e2e-test/"'):len(t)-1]
                        flat_json_list.append(flat_json)
    with open(r'flatten_data.json', mode='w') as j_flat_file:
        json.dump(flat_json_list, j_flat_file)

def commits_breakdown(changed_files):
    collect_date = datetime.now()
    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        collect_date = datetime.fromisoformat(schema['date'])
    file_changes = dict()
    for file in changed_files:
        with open(file, 'r') as f_reader:
            reader = json.load(f_reader)
            ch_3 = 0
            ch_14 = 0
            ch_56 = 0
            for item in reader:
                for ch in item["commits"]:
                    if datetime.fromisoformat(ch['committed'].replace('Z', '')) > collect_date - timedelta(days=3):
                        ch_3 += 1
                    if datetime.fromisoformat(ch['committed'].replace('Z', '')) > collect_date - timedelta(days=14):
                        ch_14 += 1
                    if datetime.fromisoformat(ch['committed'].replace('Z', '')) > collect_date - timedelta(days=56):
                        ch_56 += 1
                file_changes[item["path"]] = (ch_3, ch_14, ch_56)
    return file_changes


def test_failure_breakdown(failed_test_files):
    collect_date = datetime.now()
    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        collect_date = datetime.fromisoformat(schema['date'])
    failure_breakdown = dict()
    for f in failed_test_files:
        with open(f, 'r') as f_reader:
            reader = json.load(f_reader)
            for item in reader:
                for t in item['failed_tests']:
                    if t not in failure_breakdown:
                        failure_breakdown[t] = [0, 0, 0, 0]
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=7):
                        failure_breakdown[t][0] += 1
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=14):
                        failure_breakdown[t][1] += 1
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=28):
                        failure_breakdown[t][2] += 1
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=56):
                        failure_breakdown[t][3] += 1

    return failure_breakdown

# # load data
# dataset = loadtxt('pima-indians-diabetes.csv', delimiter=",")
#
# # split data into X and y
# X = dataset[:, 0:8]
# Y = dataset[:, 8]
#
# # split data into train and test sets
# seed = 7
# test_size = 0.2
# X_train, X_test, y_train, y_test = train_test_split(X, Y, test_size=test_size, random_state=seed)
#
# # fit model no training data
# model = XGBClassifier()
# model.fit(X_train, y_train)
#
# # make predictions for test data
# y_pred = model.predict(X_test)
# predictions = [round(value) for value in y_pred]
#
# # evaluate predictions
# accuracy = accuracy_score(y_test, predictions)
# print("Accuracy: %.2f%%" % (accuracy * 100.0))


if __name__ == "__main__":
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_19_8_18_00.js')
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_18_8_12_00.js')
    # change_priorities('/Users/rarviv/Downloads/prowjobs/prowjobs_19_8_8_00.js')
    flatten_jsons()
    create_csv()
