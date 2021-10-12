***Note: This file isn't done yet - some parts of the text are simply placeholders TODO - delte scaffold when done***

# Test prioritization in the CI\CD cycle (Red Hat OpenShift case study)
This is the code for the final project in the course "Workshop: Projects with the Industry and Academia" (IDC, Herzliya August 2021)

#### Project Status: [Active, Completed]

## Project Intro/Objective

The purpose of this project is to be a POC in test prioritization as part of a CI\CD cycle.
More specifically, in this project we aimed at showing the feasibility of a specific predictive test selection scheme in a Red Hat project.
The test selection scheme is based on the article ["Predictive Test Selection" by Facebook reseacrh (Machalica et al., 2019)](https://research.fb.com/wp-content/uploads/2020/12/Predictive-Test-Selection.pdf) (hereinafter referd to as "the FB article").
The Red Hat product we implemented this on is the [OpenShift project](https://github.com/openshift/origin).
As will be detailed below, the heavy lifting of this implementation (in terms of coding and computation resources, run time etc.) was creating a coherent dataset of sufficient size.


### Partner
* Red Hat Inc.
* https://www.redhat.com/en
* Partner contacts:
   * Dr. Ilya Kolchinsky, ikolchin@redhat.com
   * Gil Klein, gklein@redhat.com

### Methods Used
* XGBClassifier (xgboost)
* XGBRegressor (xgboost)
* train_test_split (sklearn)
* accuracy_score (sklearn)
* LabelEncoder (sklearn)

### Technologies
* xgboost
* sklearn
* Python (version 3.9.0)
* PyCharm 

## Project Description
This project has 2 parts:
1. Fetching and preparing the data that links code changessets with the respective tests that were run on them (in the CI\CD process).
2. Running ML algorithm\s on said data to create code that, given a changeset and a list of tests, will output the probabilty that each test will fail in the CI\CD process. 
3. The prioritized list will be used to select which tests will be run given future code changesets (since running all tests for each changeset is infeasible).

In more detail
--------------

**Part no.1** is accomplished by scraping 2 resources (of raw metdata): the [OpenShift Github homepage](https://github.com/openshift/origin) and [the project's CI website](https://prow.ci.openshift.org/). The code that scrapes the data is in 3 different files (see below), each of which produces data files that are ready to be pre-processed and then "fed" into the ML model in part no.2

\*The code for this part is in the *scraper* folder


**Part no.2** is accomplished by taking the output from scraper (the former part) and parsing it. The result is a flatten json and a csv file to be used by the xgboost. The learning used for now is the XGBClassifier altough XGBRegressor is also implemented.
The main methods are (1) create_flatten_json, (2) create_csv, (3) learn and (4) predict.
The data for the learning validations and tests ids is splitted in the following manner:
* Split between history data before the last week and the data from last week.
* The history data is then splitted again in a ratio of 80/20 where 80% is used for learning and 20% for validating.
* The last week data is used for testing the model.

The flatten json, csv file ,model, validation data and test data are saved into output folder. 
   
\*The code for this part is in the *Learner* folder

## Project History and Evolution

The main challenge in this project was getting the raw data, identifying and extracting the relevant parts in it and finally prepare it in a scheme like in the FB article.
The first challenege was to choose a project that has enough "meat" (e.g. pull requests, large test suites etc.). With the advice of Gil Klein from Red Hat, the OpenShift project was selected. 
The second part was a long and tedious cycle of trial & error that invloved vieweing and manually analyzing the structure of OpenShift's CI system, its test-running outputs, the way it ran tests and documented their state (e.g. fail\success\skip) etc.
From all the data related challeneges, the one that took the most time was to create a mapping between the a test's "name"\"identifier" (also referd to as test's "locator" in RedHat's parlance) and the file that contains that test in the [OpenShift project's repo](https://github.com/openshift/origin). That mapping is needed for later use by the learning algorithm. Eventually we were able to find a good-enough mapping. Also, in order to make the program run in reasonalbe time, we chose to calculate an "alleviated" version of the "real world": once a valid mapping (i.e. a valid path in the github repo) was found, no future attempts were made to map a test locator to its file. This assumption is "alleviated" since in the real world, a given test locator can be mapped to different file\s at different times.

## Files description
    .
    ├── README.md                                            # This file
    ├── scraper                                              # Folder containing the code that creates the data files
    │   ├── fetch_files_history.py                           # Fetches changes history of the files in the OpenShift project
    │   ├── create_tests_to_paths_mapping.py                 # Maps between test "locators" (i.e. the string used to run them in CI\CD) and the path of the file test (in the OpenShift Github)
    │   ├── scraper_changeset_to_all_tests_locators_only.py  # Creates a list of code changesets. Each changeset is mapped to its metadata and a list of tests run on this changeset
    │   ├── CONSTS.py                                        # Holds the shared configuration values and constants used by files in this folder
    │   ├── requirements.txt                                 # Specifies which packages were used by files in this folder
    │   └── sample_data                                      # Contains the output of python scripts
    |       ├── changeset_to_tests                           # Contains files created by scraper_changeset_to_all_tests_locators_only.py
    |       ├── files_changes_history                        # Contains files created by fetch_files_history.py 
    |       └── tests_locators_to_paths                      # Contains files created by create_tests_to_paths_mapping.py
    ├── Learner                                              # Folder containing the code that processes the data files
    │   ├── TestLearner.py                                   # Prepares the flatten json and csv from the scraper's output, and learns and predicts using xgboost
    │   ├── requirements.txt                                 # Specifies which packages were used by files in this folder
    │   ├── learner_schema.json                              # json schema file
    │   └── output                                           # output directory


## Getting Started

1. Clone this repo (for help see this [tutorial](https://help.github.com/articles/cloning-a-repository/)).

2. To run any python code, you first need to install the required packages. It's recommended that you do this on a virtual environment (for help see [official documentation](https://docs.python.org/3/tutorial/venv.html))

3. To create up-to-date data (*scraper* folder)
   
   3.1 Run the 3 files (fetch_files_history.py, create_tests_to_paths_mapping.py, scraper_changeset_to_all_tests_locators_only.py). Each is its own process and can run simultaneously to others. 
   
   3.2 Notes + Runtime:
    - For the files that use the Github API (fetch_files_history.py, scraper_changeset_to_all_tests_locators_only.py) - see the relevant [documentation](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting).
**\*Note\*** that the code expects you to have a file called credentials.py with you Github username and token.
    - For the file create_tests_to_paths_mapping.py - this may take a long time (depending on your needs). The data we have in this repo has been collected in a time span of ~40 hours.

4. To run the learner and predictor (given data is present) (*Learner* folder)
   
   4.1 In order to run the code the Learner will use all the data under scraper/sample_data folder. The Learner will first build of it a flattened json that will translated to CSV file.
   The outputs expected are flatten_data.json, prs.csv and pkl files of the xgboost trained model and the test validation files. In the end of the test of the model the program will output the confusion matrix and classification report.
   4.2 Runtime:
    - The total runtime of the parsing + learner should take no more then few minutes, for the data collected here (around 600,000 records)
    

## Featured Notebooks/Analysis/Deliverables
* The presentation summarizing this project can be found [here](https://github.com/Amannor/redhat_final_proj/blob/main/presentation/Demo_day_redhat_alon_rubi.pptx) (.pptx file)
* Todo - Maybe links to the data repo if we separate it [Notebook/Markdown/Slide DeckTitle](link)
* Todo - Maybe link to the video we'll do[Blog Post](link)


## Contributing Members

**Team Members (Contacts) : [Alon Mannor](https://github.com/amannor), [Rubi Arviv](https://github.com/rubiarviv)**

## Contact
* Feel free to contact team members with any questions or if you are interested in contributing!

#### Misc
This README template was taken from: https://github.com/sfbrigade/data-science-wg/blob/master/dswg_project_resources/Project-README-template.md
