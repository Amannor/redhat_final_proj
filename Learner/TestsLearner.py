# First XGBoost model
from numpy import loadtxt
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier, XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score
import os
import csv
import json
from sklearn.model_selection import GridSearchCV

from datetime import datetime
from datetime import timedelta
import pandas as pd
import numpy as np
import pickle
from scraper.CONSTS import SET_CONTAINING_ONLY_EMPTY_STR
import re
import math
from sklearn.model_selection import cross_val_score
from sklearn.model_selection import RepeatedKFold
from sklearn.model_selection import RepeatedStratifiedKFold
from sklearn.metrics import classification_report, confusion_matrix

github_project = 'github.com/openshift/origin/'
src_str = re.compile(github_project, re.IGNORECASE)
##########################
# Method to translate flatten json to CSV file
##########################
def create_csv():
    path = r'./output/flatten_data.json'

    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        fieldnames = schema["schema_fields"].keys()

    with open(r'./output/prs.csv', mode='w') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        with open(path, 'r') as f_reader:
            reader = json.load(f_reader)
            for item in reader:
                writer.writerow(item)



def collect_data_history():
    path_all_files = r'../scraper/all_project_files_metdata.json'
    with open(path_all_files, 'r') as f_reader:
        reader = json.load(f_reader)
        return reader


##########################
# Method to calculate minimal distance between between test file and the file in the changeset
##########################
def minimal_distance(changed_files, test_file):
    tf = src_str.sub('', test_file)
    splits_tf = tf.split('/')
    min_val = 1000
    for changed_file in changed_files:
        #remove prefix github_project which is the project we are dealing with
        cf = src_str.sub('', changed_file['filename'])
        splits_cf = cf.split('/')
        # the count is calculated according to token
        count = len(splits_cf) + len(splits_tf)
        for i in range(min(len(splits_cf) - 1, len(splits_tf) - 1)):
            if splits_tf[i] == splits_cf[i]:
                count -= 2
            else:
                break
        if count < min_val:
            min_val = count
    return min_val

##########################
# Method to calculate common tokens between test files and changesets
##########################
def common_token(changed_file, test_file):
    cf = src_str.sub('', changed_file)
    tf = src_str.sub('', test_file)
    splits_cf = cf.split('/')
    splits_tf = tf.split('/')
    count = 0
    # count common token, doesn't have to be continuous
    for i in range(min(len(splits_cf)-1, len(splits_tf)-1)):
        if splits_tf[i] == splits_cf[i]:
            count += 1
        else:
            break
    return count


##########################
# Method to flatten json
##########################
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
                            flat_json['minimal_distance'] = -1
                            flat_json['common_tokens'] = -1
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
                                flat_json['common_tokens'] = common_token(flat_json['file_name'], f_t)
                                flat_json['minimal_distance'] = minimal_distance(
                                    item['code_changes_data']['commits'][0]['commit_files'], f_t)
                                flat_json['test_status'] = 0
                                if item['tests_locator_to_state'][tests_locator] == "Failed":
                                    flat_json['test_status'] = 1
                                flat_json_list.append(flat_json)
    with open(r'./output/flatten_data.json', mode='w') as j_flat_file:
        json.dump(flat_json_list, j_flat_file)


##########################
# Method to calculate files commits in last 3/14/56 days
##########################
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


##########################
# Method to calculate tests failures breakdown in last 7/14/28/56 days
##########################
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


##########################
# Method to map locators (test name to test files)
##########################
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
                # key = item[len('e2e-test/"'):len(item) - 1]
                if item not in test_name_enum:
                    test_name_enum[item] = i
                    i += 1
                if item in test_mapping and \
                        (len(reader[item]) == 0 or set(reader[item]) == SET_CONTAINING_ONLY_EMPTY_STR):
                    continue
                # if len(reader[item]) == 0 or len(reader[item]) == 1 and reader[item][0] == '':
                #     continue
                if item not in test_mapping:
                    test_mapping[item] = reader[item]
                else:
                    test_mapping[item].extend(reader[item])
                    temp_set = set()
                    for it in test_mapping[item]:
                        if it not in temp_set:
                            temp_set.add(it)
                    test_mapping[item] = list(temp_set)
                for f_n in reader[item]:
                    if f_n not in test_file_enum:
                        test_file_enum[f_n] = j
                        j += 1
    return test_mapping, test_name_enum, test_file_enum


##########################
# Classifier or Regressor learner
##########################
def learn(is_classifier=True):
    collect_date = datetime.now()
    with open(r'learner_schema.json', 'r') as f_schema:
        schema = json.load(f_schema)
        collect_date = datetime.fromisoformat(schema['date'])
    # load data
    # for now we are dropping 'project_name' and 'test_name' which is just used for calculating the common
    # tokens and minimal distance features
    dataset = pd.read_csv(r'./output/prs.csv').drop(['project_name', 'test_name'], axis=1)
    arr = dataset.to_numpy()

    # encoding textual features like file name and file type
    # fit stage
    labelencoder1 = LabelEncoder()
    labelencoder1.fit(arr[:, 1])
    labelencoder3 = LabelEncoder()
    labelencoder3.fit(arr[:, 3])

    # split the data train data and validation data (last week)
    df_train = dataset.loc[pd.to_datetime(dataset['date']) <= collect_date]
    df_validate = dataset.loc[pd.to_datetime(dataset['date']) > collect_date]
    arr_train = df_train.to_numpy()
    arr_validate = df_validate.to_numpy()

    # split data into X and y

    # np.random.shuffle(arr_train)

    # arr_train = arr_train[0:100000, :]
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

    # encoding textual features like file name and file type
    # transform stage
    X_train[:, 0] = labelencoder1.transform(X_train[:, 0])
    X_train[:, 2] = labelencoder3.transform(X_train[:, 2])

    X_validate[:, 0] = labelencoder1.transform(X_validate[:, 0])
    X_validate[:, 2] = labelencoder3.transform(X_validate[:, 2])

    label_encoder = LabelEncoder()
    y_train = label_encoder.fit_transform(y_train)

    # X_train_r = X_train
    # y_train_r =y_train

    # split the train data to train and test
    # X_train, X_test, y_train, y_test = train_test_split(X_train, y_train, test_size=test_size, random_state=seed)

    # fit classifier or regressor model fit and save the model to pickle file
    if is_classifier:
        model = XGBClassifier(scale_pos_weight=9, verbosity=2, use_label_encoder=False)
        model.fit(X_train, y_train)
        pickle.dump(model, open('./output/classifier_model.pkl', 'wb'))
    else:
        # # define model
        # model = XGBClassifier()
        # # define grid
        # weights = [1, 10, 25, 50, 75, 99, 100, 1000]
        # param_grid = dict(scale_pos_weight=weights)
        # # define evaluation procedure
        # cv = RepeatedStratifiedKFold(n_splits=10, n_repeats=3, random_state=1)
        # # define grid search
        # grid = GridSearchCV(estimator=model, param_grid=param_grid, n_jobs=-1, cv=cv, scoring='roc_auc')
        # # execute the grid search
        # label_encoder = LabelEncoder()
        # y_train_r = label_encoder.fit_transform(y_train_r)
        # grid_result = grid.fit(X_train_r, y_train_r)
        # # report the best configuration
        # print("Best: %f using %s" % (grid_result.best_score_, grid_result.best_params_))
        # # report all configurations
        # means = grid_result.cv_results_['mean_test_score']
        # stds = grid_result.cv_results_['std_test_score']
        # params = grid_result.cv_results_['params']
        # for mean, stdev, param in zip(means, stds, params):
        #     print("%f (%f) with: %r" % (mean, stdev, param))
        model = XGBRegressor(scale_pos_weight=9, use_label_encoder=False)
        # evaluate model
        model.fit(X_train, y_train)
        pickle.dump(model, open('./output/regressor_model.pkl', 'wb'))

    # save the test and validate data
    pickle.dump(X_validate, open('./output/X_validate.pkl', 'wb'))
    pickle.dump(y_validate, open('./output/y_validate.pkl', 'wb'))


def cut_off(x, th=0.7):
    if x >= th:
        return 1
    return 0


##########################
# Predict classifier
##########################
def predict(is_classifier=True):

    if is_classifier:
        loaded_model = pickle.load(open('./output/classifier_model.pkl', 'rb'))
        # X_test = pickle.load(open('./output/X_test.pkl', 'rb'))
        # y_test = pickle.load(open('./output/y_test.pkl', 'rb'))
        # # make predictions for test data
        # y_pred = loaded_model.predict(X_test)
        # predictions = np.array([int(round(value)) for value in y_pred])
        #
        # y_test = y_test.astype('int32')
        # accuracy = accuracy_score(y_test, predictions)
        # print("Validation Accuracy: %.2f%%" % (accuracy*100))

    else:
        loaded_model = pickle.load(open('./output/regressor_model.pkl', 'rb'))
    # make predictions for validation data
    X_validate = pickle.load(open('./output/X_validate.pkl', 'rb'))
    y_validate = pickle.load(open('./output/y_validate.pkl', 'rb'))

    y_pred = loaded_model.predict(X_validate)
    if is_classifier:
        predictions = np.array([int(round(value)) for value in y_pred])
    else:
        predictions = np.array([int(cut_off(value, 0.7)) for value in y_pred])
    y_validate = y_validate.astype('int32')

    print('confusion matrix: ')
    print(confusion_matrix(y_validate, predictions))
    print(classification_report(y_validate, predictions))


if __name__ == "__main__":
    ##########################################################
    # it is not necessary to run first 2 methods each time
    flatten_jsons()
    create_csv()
    #########################################################
    learn(False)
    predict(False)


