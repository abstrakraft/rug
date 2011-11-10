#!/usr/bin/python
import os
import sys
import getopt
import xml.dom.minidom

import git

def main():
	if (len(sys.argv) < 2) or not gitri_commands.has_key(sys.argv[1]):
		#TODO: write usage
		print 'gitri usage'
	else:
		cmd = gitri_commands[sys.argv[1]]
		[optlist, args] = getopt.gnu_getopt(sys.argv[2:], cmd[2])
		if cmd[1]:
			cmd[0](Project.find_project(), optlist, *args)
		else:
			cmd[0](optlist, *args)

class GitriError(StandardError):
	pass

class InvalidProjectError(GitriError):
	pass

GITRI_DIR = '.gitri'

class Project(object):
	def __init__(self, dir):
		self.dir = os.path.abspath(dir)
		#Verify validity
		if not self.valid_project(self.dir):
			raise InvalidProjectError('not a valid gitri project')

		#Create convenient properties
		self.gitri_dir = os.path.join(self.dir, GITRI_DIR)
		self.manifest_dir = os.path.join(self.gitri_dir, 'manifest')
		self.manifest_repo = git.Repo(self.manifest_dir)

	def read_manifest(self):
		'read in the manifest.xml file.  Project methods should only call this function if necessary.'
		self.remotes = {}
		self.repos = []
		self.default = {}

		manifest = xml.dom.minidom.parse(os.path.join(self.manifest_dir, 'manifest.xml'))
		m = manifest.childNodes[0]
		if m.localName != 'manifest':
			raise GitriError('malformed manifext.xml: no manifest element')
		for node in m.childNodes:
			if node.localName == 'default':
				self.default.update(dict(node.attributes.items()))
			elif node.localName == 'remote':
				remote = dict(node.attributes.items())
				#TODO: detect duplicates
				self.remotes[remote['name']] = remote
			elif (node.localName == 'project') or (node.localName == 'repo'):
				repo = {}
				repo.update(self.default)
				repo.update(dict(node.attributes.items()))
				#TODO: detect duplicates
				self.repos.append(repo)

	@classmethod
	def find_project(cls, dir = None):
		'climb up the directory tree looking for a valid gitri project'

		if dir == None:
			dir = os.getcwd()

		head = dir
		while head:
			try:
				return cls(head)
			except InvalidProjectError:
				if head == '/':
					head = None
				else:
					(head, tail) = os.path.split(head)

		raise InvalidProjectError('not a valid gitri project')

	@classmethod
	def clone(cls, optlist, url, dir=None, revset=None):
		'clone an existing gitri repository'

		#calculate directory
		if dir == None:
			basename = os.path.basename(url)
			if len(basename) == 0:
				basename = os.path.basename(url[:-1])
			dir = os.path.splitext(basename)[0]
		dir = os.path.abspath(dir)

		#verify directory doesn't exist
		if os.path.exists(dir):
			raise GitriError('Directory already exists')

		#clone manifest repo into gitri directory
		git.Repo.clone(url, dir=os.path.join(dir, GITRI_DIR, 'manifest'), rev=revset)

		#verify valid manifest
		manifest_src = os.path.join(dir, GITRI_DIR, 'manifest', 'manifest.xml')
		if not os.path.exists(manifest_src):
			raise GitriError('invalid manifest repo: no manifest.xml')

		#checkout revset
		p = cls(dir)
		p.checkout({})

	@classmethod
	def valid_project(cls, dir):
		'verify the minimum qualities necessary to be called a gitri project'
		manifest_dir = os.path.join(dir, GITRI_DIR, 'manifest')
		return git.Repo.valid_repo(manifest_dir) and \
			os.path.exists(os.path.join(manifest_dir, 'manifest.xml'))

	def get_branches(self, repo, repo_conf):
		#gitri_branch = 'gitri/%s/%s/%s' % (self.revset(), r['remote'], r.get('revision', 'HEAD'))
		#bookmark_branch = 'refs/bookmarks/%s/%s/%s' % (self.revset(), r['remote'], r.get('revision', 'HEAD'))
		revision = repo_conf.get('revision', 'HEAD')
		if revision == 'HEAD':
			start = len('refs/remotes/%s/' % repo_conf['remote'])
			revision = repo.symbolic_ref('refs/remotes/%s/HEAD' % repo_conf['remote'])[start:]
		ret = {}
		ret['gitri'] = revision
		if repo.valid_sha(revision):
			ret['bookmark'] = revision
			ret['remote'] = revision
		else:
			ret['bookmark'] = 'refs/gitri/%s/%s/%s' % (self.revset(), repo_conf['remote'], revision)
			ret['remote'] = '%s/%s' % (repo_conf['remote'], revision)

		return ret

	def revset(self):
		'return the name of the current revset'
		return self.manifest_repo.head()

	def checkout(self, optlist, revset=None):
		'check out a revset'

		#Checkout manifest manifest
		if revset is None:
			revset = self.revset()
		#Always throw away local gitri changes - uncommitted changes to the manifest.xml file are lost
		self.manifest_repo.checkout(revset, force=True)

		#reread manifest
		self.read_manifest()

		for r in self.repos:
			path = os.path.abspath(os.path.join(self.dir, r['path']))
			url = self.remotes[r['remote']]['fetch'] + '/' + r['name']

			#if the repo doesn't exist, clone it
			if not git.Repo.valid_repo(path):
				repo = git.Repo.clone(url, dir=path, remote=r['remote'], rev=r.get('revision'))
			else:
				repo = git.Repo(path)

			#Verify remotes
			if r['remote'] not in repo.remote_list():
				repo.remote_add(r['remote'], url)
			else:
				#Currently easier to just set the remote URL rather than check and set if different
				repo.remote_set_url(r['remote'], url)

			#Fetch from remote
			#TODO:decide if we should always do this here.  Sometimes have to, since we may not have
			#seen this remote before
			repo.fetch(r['remote'])

			branches = self.get_branches(repo, r)

			#create gitri and bookmark branches if they don't exist
			print branches
			if not repo.valid_ref(branches['gitri']):
				repo.branch_create(branches['gitri'], branches['remote'])
			if not repo.valid_ref(branches['bookmark']):
				repo.update_ref(branches['bookmark'], branches['remote'])

			#checkout the gitri branch
			repo.checkout(branches['gitri'])

	def fetch(self, optlist, repos=None):
		self.read_manifest()

		if repos is None:
			repos = self.repos
		else:
			#TODO: turn list of strings into repos
			pass

		self.manifest_repo.fetch()

		for r in repos:
			path = os.path.abspath(os.path.join(self.dir, r['path']))
			if git.Repo.valid_repo(path):
				repo = git.Repo(path)
				repo.fetch(r['remote'])
				repo.remote_set_head(r['remote'])

	def update(self, optlist, repos=None):
		self.read_manifest()

		if repos is None:
			repos = self.repos
		else:
			#TODO: turn list of strings into repos
			pass

		#TODO:fetch?

		#TODO:update manifest

		for r in repos:
			path = os.path.abspath(os.path.join(self.dir, r['path']))

			if git.Repo.valid_repo(path):
				repo = git.Repo(path)
				branches = self.get_branches(repo, r)
				#Check if there are no changes
				if repo.rev_parse(repo.head()) == repo.rev_parse(branches['remote']):
					print '%s is up to date with upstream repo: no change' % r['name']
				elif repo.is_descendant(branches['remote']):
					print '%s is ahead of upstream repo: no change' % r['name']
				#Fast-Forward if we can
				elif repo.can_fastforward(branches['remote']):
					print '%s is being fast-forward to upstream repo' % r['name']
					repo.merge(branches['remote'])
					repo.update_ref(branches['bookmark'], 'HEAD')
				#otherwise rebase local work
				elif repo.is_descendant(branches['bookmark']):
					if repo.dirty():
						#TODO: option to stash, rebase, then reapply?
						print '%s has local uncommitted changes and cannot be rebased. Skipping this repo.' % r['name']
					else:
						print '%s is being rebased onto upstream repo' % r['name']
						[ret,out,err] = repo.rebase(branches['bookmark'], onto=branches['remote'])
						if ret:
							print out
						else:
							repo.update_ref(branches['bookmark'], branches['remote'])
				#Fail
				elif repo.head() != branches['gitri']:
					print repo.head(), branches['gitri']
					print '%s has changed branches and cannot be safely updated. Skipping this repo.' % r['name']
				else:
					#Weird stuff has happened - right branch, wrong relationship to other bookmark
					print 'The current branch in %s has been in altered in an unusal way and must be manually updated.' % r['name']
			else:
				url = self.remotes[r['remote']]['fetch'] + '/' + r['name']
				if r.has_key('revision'):
					repo = git.Repo.clone(url, dir=path, remote=r['remote'], rev=r['revision'], local_branch=branches['gitri'])
				else:
					repo = git.Repo.clone(url, dir=path, remote=r['remote'], local_branch=branches['gitri'])
				repo.update_ref(branches['bookmark'], 'HEAD')

	#TODO: define precisely what this should do
	#def reset(self, optlist=[], repos=None):
	#	if repos is None:
	#		repos = self.repos
	#	gitri_branch = 'gitri/%s/%s' % (self.origin(), self.revset())
	#
	#	if optlist.has_key('soft'):
	#		mode = git.Repo.SOFT
	#	elif optlist.has_key('mixed'):
	#		mode = git.Repo.MIXED
	#	elif optlist.has_key('hard'):
	#		mode = git.Repo.HARD
	#	
	#	for r in repos:
	#		r.checkout(gitri_branch, mode = mode)

gitri_commands = {
	'clone': (Project.clone, False, ''),
	'checkout': (Project.checkout, True, ''),
	'fetch': (Project.fetch, True, ''),
	'update': (Project.update, True, ''),
	#'reset': (Project.reset, True, ['soft', 'mixed', 'hard']),
	}

if __name__ == '__main__':
	main()

#The following code was necessary before manual clone was implemented in order to
#clone into a non-empty directory
#if os.path.exists(path) and (not os.path.isdir(path)):
#	GitriError('path %s already exists and is not a directory' % (path,))
#elif os.path.isdir(path) and (os.listdir(path) != []):
#	tmp_path = tempfile(dir='.')
#	#todo: proper path join (detect foreign OS)
#	repo = git.Repo.clone(self.remotes[p['remote']]['fetch'] + '/' + p['name'], tmp_path)
#	#move tmp_path to path
#	#rmdir tmp_path
#else:
#	#path is an empty directory, or doesn't exist
#	#todo: proper path join (detect foreign OS)
