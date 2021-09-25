MAX_JOBS = 4000
OUT_FILE = "all_jobs"
DATA_FOLDER = "sample_data"
DEFAULT_REQUEST_TIMEOUT_SECONDS = 1800
OWNER = "openshift"
REPO = "origin"
SET_CONTAINING_ONLY_EMPTY_STR = set()
SET_CONTAINING_ONLY_EMPTY_STR.add("")
TST_FETCHING_BASE_URL = r"https://prow.ci.openshift.org/"
MAIN_OPENSHIFT_URL = 'https://prow.ci.openshift.org/job-history/gs/origin-ci-test/pr-logs/directory/pull-ci-openshift-origin-master-e2e-gcp?buildId'
GITHUB_API_BASE_URL  = r'https://api.github.com'
GITHUB_API_FILE_COMMITS_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/commits?path={PATH_TO_FILE}'
GITHUB_API_TREE_SUFFIX_PATTERN = r'/repos/{owner}/{repo}/git/trees/{tree_sha}' #From https://docs.github.com/en/rest/reference/git#trees