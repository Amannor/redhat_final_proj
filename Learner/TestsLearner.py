# First XGBoost model
from numpy import loadtxt
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix
from sklearn.metrics import accuracy_score
import os
import csv
import json

from datetime import datetime
from datetime import timedelta
import pandas as pd
import numpy as np
import pickle


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


def minimal_distance(changed_files, test_file):
    tf = test_file.replace('github.com/openshift/origin/', '')
    splits_tf = tf.split('/')
    min_val = 1000
    for changed_file in changed_files:
        cf = changed_file['filename'].replace('github.com/openshift/origin/', '')
        splits_cf = cf.split('/')
        count = len(splits_cf) + len(splits_tf)
        for i in range(min(len(splits_cf) - 1, len(splits_tf) - 1)):
            if splits_tf[i] == splits_cf[i]:
                count -= 2
            else:
                break
        if count < min_val:
            min_val = count
    return min_val


def common_token(changed_file, test_file):
    cf = changed_file.replace('github.com/openshift/origin/', '')
    tf = test_file.replace('github.com/openshift/origin/', '')
    splits_cf = cf.split('/')
    splits_tf = tf.split('/')
    count = 0
    for i in range(min(len(splits_cf)-1, len(splits_tf)-1)):
        if splits_tf[i] == splits_cf[i]:
            count += 1
    return count


def flatten_jsons():
    collect_date = datetime.now()
    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        collect_date = datetime.fromisoformat(schema['date'])

    path = r'../scraper/sample_data/files_changes_history'
    path_tests = r'../scraper/sample_data/tests_locators_to_paths'
    path_changeset = r'../scraper/sample_data/changeset_to_tests'
    history = collect_data_history()
    changed_files = []
    failed_test_files = []
    test_locators = []
    # r=root, d=directories, f = files
    for r, d, f in os.walk(path):
        for file in f:
            changed_files.append(os.path.join(r, file))
    for r, d, f in os.walk(path_tests):
        for file in f:
            test_locators.append(os.path.join(r, file))
    for r, d, f in os.walk(path_changeset):
        for file in f:
            failed_test_files.append(os.path.join(r, file))

    test_mapping, test_name_enum, test_file_enum = test_mapper(test_locators)
    file_changes = commits_breakdown(changed_files)
    failure_breakdown = test_failure_breakdown(failed_test_files)

    flat_json_list = list()
    for f in failed_test_files:
        print(f)
        with open(f, 'r') as f_reader:
            reader = json.load(f_reader)
            for item in reader:
                date_entry = datetime.fromisoformat(item['date'])
                f_size = len(item['code_changes_data']['commits'][0]['commit_files'])
                as_size = len(item['code_changes_data']['assignees'])
                for fn in item['code_changes_data']['commits'][0]['commit_files']:
                    last_token = fn['filename'].rfind('/')
                    ext = fn['filename'].rfind('.')
                    t_size = len(item['tests_locator_to_state'])
                    for tests_locator in item['tests_locator_to_state']:
                        if item['tests_locator_to_state'][tests_locator] != "Passed" and \
                                item['tests_locator_to_state'][tests_locator] != "Failed":
                            continue
                        if tests_locator not in test_mapping:
                            flat_json = dict()
                            flat_json['date'] = date_entry.strftime("%Y-%m-%dT%H:%M:%S")
                            flat_json['file_name'] = fn['filename']
                            flat_json['num_files_changed'] = f_size
                            if last_token < ext:
                                flat_json['file_extension'] = fn['filename'][ext + 1:len(fn['filename'])]
                            else:
                                flat_json['file_extension'] = ''
                            flat_json['num_target_tests'] = t_size
                            if fn['filename'] in file_changes:
                                flat_json['number_changes_3d'] = file_changes[fn['filename']][0]
                                flat_json['number_changes_14d'] = file_changes[fn['filename']][1]
                                flat_json['number_changes_56d'] = file_changes[fn['filename']][2]
                            else:
                                flat_json['number_changes_3d'] = 0
                                flat_json['number_changes_14d'] = 0
                                flat_json['number_changes_56d'] = 0
                            flat_json['project_name'] = ''
                            flat_json['distinct_authors'] = as_size
                            if tests_locator in failure_breakdown:
                                flat_json['failed_7d'] = failure_breakdown[tests_locator][0]
                                flat_json['failed_14d'] = failure_breakdown[tests_locator][1]
                                flat_json['failed_28d'] = failure_breakdown[tests_locator][2]
                                flat_json['failed_56d'] = failure_breakdown[tests_locator][3]
                            else:
                                flat_json['failed_7d'] = 0
                                flat_json['failed_14d'] = 0
                                flat_json['failed_28d'] = 0
                                flat_json['failed_56d'] = 0
                            flat_json['minimal_distance'] = 0
                            flat_json['common_tokens'] = 0
                            test_name = tests_locator[len('e2e-test/"'):len(tests_locator) - 1]
                            if test_name in test_name_enum:
                                flat_json['test_name'] = test_name_enum[test_name]
                            else:
                                flat_json['test_name'] = 0
                            flat_json['test_file'] = 0
                            flat_json['test_status'] = 0
                            if item['tests_locator_to_state'][tests_locator] == "Failed":
                                flat_json['test_status'] = 1
                            flat_json_list.append(flat_json)
                        else:
                            for f_t in test_mapping[tests_locator]:
                                flat_json = dict()
                                flat_json['date'] = date_entry.strftime("%Y-%m-%dT%H:%M:%S")
                                flat_json['file_name'] = fn['filename']
                                flat_json['num_files_changed'] = f_size
                                if last_token < ext:
                                    flat_json['file_extension'] = fn['filename'][ext + 1:len(fn['filename'])]
                                else:
                                    flat_json['file_extension'] = ''
                                flat_json['num_target_tests'] = t_size
                                if fn['filename'] in file_changes:
                                    flat_json['number_changes_3d'] = file_changes[fn['filename']][0]
                                    flat_json['number_changes_14d'] = file_changes[fn['filename']][1]
                                    flat_json['number_changes_56d'] = file_changes[fn['filename']][2]
                                else:
                                    flat_json['number_changes_3d'] = 0
                                    flat_json['number_changes_14d'] = 0
                                    flat_json['number_changes_56d'] = 0
                                flat_json['project_name'] = ''
                                flat_json['distinct_authors'] = as_size
                                if tests_locator in failure_breakdown:
                                    flat_json['failed_7d'] = failure_breakdown[tests_locator][0]
                                    flat_json['failed_14d'] = failure_breakdown[tests_locator][1]
                                    flat_json['failed_28d'] = failure_breakdown[tests_locator][2]
                                    flat_json['failed_56d'] = failure_breakdown[tests_locator][3]
                                else:
                                    flat_json['failed_7d'] = 0
                                    flat_json['failed_14d'] = 0
                                    flat_json['failed_28d'] = 0
                                    flat_json['failed_56d'] = 0
                                test_name = tests_locator[len('e2e-test/"'):len(tests_locator) - 1]
                                if test_name in test_name_enum:
                                    flat_json['test_name'] = test_name_enum[test_name]
                                else:
                                    flat_json['test_name'] = 0
                                if f_t in test_file_enum:
                                    flat_json['test_file'] = test_file_enum[f_t]
                                else:
                                    flat_json['test_file'] = 0
                                flat_json['minimal_distance'] = common_token(flat_json['file_name'],
                                                                             flat_json['test_file'])
                                flat_json['common_tokens'] = minimal_distance(
                                    item['code_changes_data']['commits'][0]['commit_files'],
                                    flat_json['test_file'])
                                flat_json['test_status'] = 0
                                if item['tests_locator_to_state'][tests_locator] == "Failed":
                                    flat_json['test_status'] = 1
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
                for f_t in item['tests_locator_to_state']:
                    if item['tests_locator_to_state'][f_t] != 'Failed':
                        continue
                    if f_t not in failure_breakdown:
                        failure_breakdown[f_t] = [0, 0, 0, 0]
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=7):
                        failure_breakdown[f_t][0] += 1
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=14):
                        failure_breakdown[f_t][1] += 1
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=28):
                        failure_breakdown[f_t][2] += 1
                    if datetime.fromisoformat(item['date'].replace('Z', '')) > collect_date - timedelta(days=56):
                        failure_breakdown[f_t][3] += 1

    return failure_breakdown


def test_mapper(test_locators):
    test_mapping = dict()
    test_name_enum = dict()
    test_file_enum = dict()
    i = 1
    j = 1
    for f in test_locators:
        with open(f, 'r') as f_reader:
            reader = json.load(f_reader)
            for item in reader:
                key = item[len('e2e-test/"'):len(item) - 1]
                if key not in test_name_enum:
                    test_name_enum[key] = i
                    i += 1
                test_mapping[key] = reader[item]
                for f_n in reader[item]:
                    if f_n not in test_file_enum:
                        test_file_enum[f_n] = j
                        j += 1
    return test_mapping, test_name_enum, test_file_enum


def learn():
    collect_date = datetime.now()
    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        collect_date = datetime.fromisoformat(schema['date'])
    # load data
    # for now we are dropping 'project_name'
    dataset = pd.read_csv(r'prs.csv').drop(['project_name', 'test_name'], axis=1)
    arr = dataset.to_numpy()

    labelencoder1 = LabelEncoder()
    labelencoder1.fit(arr[:, 1])
    labelencoder3 = LabelEncoder()
    labelencoder3.fit(arr[:, 3])

    df_train = dataset.loc[pd.to_datetime(dataset['date']) <= collect_date]
    df_validate = dataset.loc[pd.to_datetime(dataset['date']) > collect_date]
    arr_train = df_train.to_numpy()
    arr_validate = df_validate.to_numpy()

    # split data into X and y

    X_train = arr_train[:, 1:16]
    X_validate = arr_validate[:, 1:16]
    y_train = arr_train[:, 16]
    y_validate = arr_validate[:, 16]

    # split data into train and test sets
    seed = 7
    test_size = 0.2

    # set missing values to 0
    X_train[X_train == '?'] = 0
    X_validate[X_validate == '?'] = 0

    X_train[:, 0] = labelencoder1.fit_transform(X_train[:, 0])
    X_train[:, 2] = labelencoder3.fit_transform(X_train[:, 2])

    X_validate[:, 0] = labelencoder1.fit_transform(X_validate[:, 0])
    X_validate[:, 2] = labelencoder3.fit_transform(X_validate[:, 2])


    X_train, X_test, y_train, y_test = train_test_split(X_train, y_train, test_size=test_size, random_state=seed)

    # fit model no training data
    # model = XGBClassifier(learning_rate=0.1,
    #                       n_estimators=1000,
    #                       max_depth=5,
    #                       min_child_weight=1,
    #                       gamma=0,
    #                       subsample=0.8,
    #                       colsample_bytree=0.8,
    #                       nthread=4,
    #                       seed=27)
    model = XGBClassifier(verbosity=2, use_label_encoder=False)
    model.fit(X_train, y_train)
    pickle.dump(model, open('model.pkl', 'wb'))
    pickle.dump(X_validate, open('X_validate.pkl', 'wb'))
    pickle.dump(y_validate, open('y_validate.pkl', 'wb'))
    pickle.dump(X_test, open('X_test.pkl', 'wb'))
    pickle.dump(y_test, open('y_test.pkl', 'wb'))


def predict():
    loaded_model = pickle.load(open('model.pkl', 'rb'))
    X_test = pickle.load(open('X_test.pkl', 'rb'))
    y_test = pickle.load(open('y_test.pkl', 'rb'))
    # make predictions for test data
    y_pred = loaded_model.predict(X_test)
    predictions = np.array([int(round(value)) for value in y_pred])
    y_test=y_test.astype('int32')
    accuracy = accuracy_score(y_test, predictions)

    print("Validation Accuracy: %.2f%%" % (accuracy*100))

    X_validate = pickle.load(open('X_validate.pkl', 'rb'))
    y_validate = pickle.load(open('y_validate.pkl', 'rb'))

    y_pred = loaded_model.predict(X_validate)
    predictions = np.array([int(round(value)) for value in y_pred])
    y_validate=y_validate.astype('int32')
    accuracy = accuracy_score(y_validate, predictions)

    print("Test Accuracy: %.2f%%" % (accuracy*100))


if __name__ == "__main__":
    # not necessary to run first 2 function each time ##########
    flatten_jsons()
    create_csv()
    ############################################################
    learn()
    predict()


