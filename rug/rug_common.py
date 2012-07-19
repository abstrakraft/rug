RUG_DIR = '.rug'
#TODO: should this be configurable or in the manifest?
RUG_SHA_RIDER = 'refs/rug/sha_rider'
RUG_DEFAULT_DEFAULT = {'revision': 'master', 'vcs': 'git'}
RUG_CONFIG = 'config'
RUG_REPO_CONFIG_SECTION = 'repoconfig'
RUG_CANDIDATE_TEMPLATES = ['%s', '%s/.rug/manifest', '%s/manifest']

def remote_join(remote, name):
	return remote.rstrip('/') + '/' + name.lstrip('/')
