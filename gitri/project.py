#!/usr/bin/env python
import os
import sys
import xml.dom.minidom

import manifest
import git

class GitriError(StandardError):
	pass

class InvalidProjectError(GitriError):
	pass

GITRI_DIR = '.gitri'
#TODO: should this be configurable or in the manifest?
GITRI_SHA_RIDER = 'gitri/sha_rider'

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
		(self.remotes, self.repos) = manifest.read(os.path.join(self.manifest_dir, 'manifest.xml'))

	def load_repos(self):
		for path in self.repos:
			abs_path = os.path.abspath(os.path.join(self.dir, path))
			if git.Repo.valid_repo(abs_path):
				self.repos[path]['repo'] = git.Repo(abs_path)
			else:
				self.repos[path]['repo'] = None

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
				if head == os.path.sep:
					head = None
				else:
					(head, tail) = os.path.split(head)

		raise InvalidProjectError('not a valid gitri project')

	@classmethod
	def clone(cls, optlist={}, url=None, dir=None, revset=None):
		'clone an existing gitri repository'

		if not url:
			raise GitriError('url must be specified')

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
		output = p.checkout()

		output = ['%s cloned into %s' % (url, dir)]
		output.append(p.checkout({}))

		return '\n'.join(output)

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

	def revset(self, optlist={}):
		'return the name of the current revset'
		return self.manifest_repo.head()

	def status(self, optlist={}):
		#TODO: this is file status - also need repo status
		self.read_manifest()
		self.load_repos()

		stat = []
		for r in self.repos.values():
			repo = r['repo']
			if repo:
				r_stat = repo.status(porcelain=True)
				if r_stat != '':
					if r['path'] == '.':
						prefix = ''
					else:
						prefix = r['path']
						if prefix[-1] != os.path.sep:
							prefix += os.path.sep
					stat.extend([s[:3]+prefix+s[3:] for s in r_stat.split('\n')])
			else:
				stat.append(' D ' + r['path'])

		return '\n'.join(stat)

	def checkout(self, optlist={}, revset=None):
		'check out a revset'

		#Checkout manifest manifest
		if revset is None:
			revset = self.revset()
		#Always throw away local gitri changes - uncommitted changes to the manifest.xml file are lost
		self.manifest_repo.checkout(revset, force=True)

		#reread manifest
		self.read_manifest()
		self.load_repos()

		for r in self.repos.values():
			url = self.remotes[r['remote']]['fetch'] + '/' + r['name']

			#if the repo doesn't exist, clone it
			repo = r['repo']
			if not repo:
				abs_path = os.path.abspath(os.path.join(self.dir, r['path']))
				repo = git.Repo.clone(url, dir=abs_path, remote=r['remote'], rev=r.get('revision'))

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
			if not repo.valid_ref(branches['gitri']):
				repo.branch_create(branches['gitri'], branches['remote'])
			if not repo.valid_ref(branches['bookmark']):
				repo.update_ref(branches['bookmark'], branches['remote'])

			#checkout the gitri branch
			repo.checkout(branches['gitri'])

		return 'revset %s checked out' % revset

	def fetch(self, optlist={}, repos=None):
		self.read_manifest()

		if repos is None:
			self.load_repos()
			repos = self.repos.values()
		else:
			#TODO: turn list of strings into repos
			pass

		self.manifest_repo.fetch()

		for r in repos:
			repo = r['repo']
			if repo:
				repo.fetch(r['remote'])
				repo.remote_set_head(r['remote'])

		#TODO:output

	def update(self, optlist={}, repos=None):
		self.read_manifest()

		if repos is None:
			self.load_repos()
			repos = self.repos.values()
		else:
			#TODO: turn list of strings into repos
			pass

		#TODO:fetch? current thinking is no: update and fetch are separate operations

		#TODO:update manifest

		output = []

		for r in repos:
			repo = r['repo']
			if repo:
				branches = self.get_branches(repo, r)
				#Check if there are no changes
				if repo.rev_parse(repo.head()) == repo.rev_parse(branches['remote']):
					output.append('%s is up to date with upstream repo: no change' % r['name'])
				elif repo.is_descendant(branches['remote']):
					output.append('%s is ahead of upstream repo: no change' % r['name'])
				#Fast-Forward if we can
				elif repo.can_fastforward(branches['remote']):
					output.append('%s is being fast-forward to upstream repo' % r['name'])
					repo.merge(branches['remote'])
					repo.update_ref(branches['bookmark'], 'HEAD')
				#otherwise rebase/merge local work
				elif repo.is_descendant(branches['bookmark']):
					if repo.dirty():
						#TODO: option to stash, rebase, then reapply?
						output.append('%s has local uncommitted changes and cannot be rebased. Skipping this repo.' % r['name'])
					else:
						#TODO: option to merge instead of rebase
						#TODO: handle merge/rebase conflicts
						#TODO: remember if we're in a conflict state
						output.append('%s is being rebased onto upstream repo' % r['name'])
						[ret,out,err] = repo.rebase(branches['bookmark'], onto=branches['remote'])
						if ret:
							output.append(out)
						else:
							repo.update_ref(branches['bookmark'], branches['remote'])
				#Fail
				elif repo.head() != branches['gitri']:
					output.append('%s has changed branches and cannot be safely updated. Skipping this repo.' % r['name'])
				else:
					#Weird stuff has happened - right branch, wrong relationship to bookmark
					output.append('The current branch in %s has been in altered in an unusal way and must be manually updated.' % r['name'])
			else:
				abs_path = os.path.abspath(os.path.join(self.dir, r['path']))
				url = self.remotes[r['remote']]['fetch'] + '/' + r['name']
				if r.has_key('revision'):
					repo = git.Repo.clone(url, dir=abs_path, remote=r['remote'], rev=r['revision'], local_branch=branches['gitri'])
				else:
					repo = git.Repo.clone(url, dir=abs_path, remote=r['remote'], local_branch=branches['gitri'])
				repo.update_ref(branches['bookmark'], 'HEAD')

		return '\n'.join(output)

	def add(self, optlist={}, dir=None):
		#TODO:options and better logic to commit shas vs branch names
		if not dir:
			raise GitriError('unspecified directory')

		self.read_manifest()

		path = os.path.abspath(dir)
		if not git.Repo.valid_repo(path):
			raise GitriError('invalid repo %s' % dir)

		rel_path = os.path.relpath(path, self.dir)
		r = self.repos.get(rel_path, None)
		if r is None:
			#TODO: handle new repos
			raise GitriError('unrecognized repo %s' % dir)
		else:
			repo = git.Repo(path)
			head = repo.head()
			#TODO: revise logic here to take care of shas/branch names, branches that have changed sha
			if repo.valid_sha(head):
				if r['revision'] == head:
					raise GitriError('no change to repo %s' % dir)
			else:
				branches = self.get_branches(repo, r)
				if repo.rev_parse(branches['remote']) == repo.rev_parse(head):
					raise GitriError('no change to repo %s' % dir)

			(remotes, repos, default) = manifest.read(os.path.join(self.manifest_dir, 'manifest.xml'), apply_default=False)
			repos[rel_path]['revision'] = head
			repos[rel_path]['unpublished'] = 'true'
			manifest.write(remotes, repos, default)

			return "%s added to manifest" % rel_path

	def publish(self, optlist={}, remote=None):
		if not remote: raise GitriError('manifest remote must be specified')
		if not remote in self.manifest_repo.remote_list(): raise GitriError('unrecognzied remote %s' % remote)

		self.read_manifest()

		error = []
		output = []

		#Verify that we can push to all unpublished remotes
		ready = True
		unpub_repos = []
		for r in self.repos.values():
			if r.get('unpublished', False):
				#TODO: verify correctness & consistency of path functions/formats throughout gitri
				path = os.path.abspath(os.path.join(self.dir, r['path']))
				repo = git.Repo(path)

				if repo.valid_sha(r['revision']):
					refspec = '%s:refs/%s' % (r['revision'], GITRI_SHA_RIDER)
					force = True
				else:
					refspec = r['revision']
					force = False
				unpub_repos.append((r, repo, refspec, force))
				if not repo.test_push(r['remote'], refspec, force=force):
					error.append('%s: %s cannot be pushed to %s' % (r['name'], r['revision'], r['remote']))
					ready = False

		#Verify that we can push to manifest repo
		#TODO: We don't always need to push manifest repo
		manifest_revision = self.manifest_repo.head()
		if self.manifest_repo.valid_sha(manifest_revision):
			manifest_refspec = '%s:refs/%s' % (manifest_revision, GITRI_SHA_RIDER)
			manifest_force = True
		else:
			manifest_refspec = manifest_revision
			manifest_force = False
		if not self.manifest_repo.test_push(remote, manifest_refspec, force=manifest_force):
			error.append('manifest branch %s cannot be pushed to %s' % (manifest_revision, r['remote']))
			ready = False

		#Error if we can't publish anything
		if not ready:
			raise GitriError('\n'.join(error))

		#Push unpublished remotes
		for (r, repo, refspec, force) in unpub_repos:
			repo.push(r['remote'], refspec, force)
			output.append('%s: pushed %s to %s' % (r['name'], r['revision'], r['remote']))

		#Rewrite manifest
		unpub_repo_paths = [r['path'] for (r, repo, refspec, force) in unpub_repos]
		manifest = xml.dom.minidom.parse(os.path.join(self.manifest_dir, 'manifest.xml'))
		xml_repos = manifest.getElementsByTagName('repo')
		for xr in xml_repos:
			if xr.attributes['path'].value in unpub_repo_paths:
				xr.attributes.removeNamedItem('unpublished')
		file = open(os.path.join(self.manifest_dir, 'manifest.xml'), 'w')
		file.write(manifest.toxml()+'\n')
		file.close()

		#Commit and push manifest
		#TODO:input commit message
		self.manifest_repo.commit(all=True, message="Gitri publish commit")
		manifest_revision = self.manifest_repo.head()
		if self.manifest_repo.valid_sha(manifest_revision):
			manifest_refspec = '%s:refs/%s' % (manifest_revision, GITRI_SHA_RIDER)
			manifest_force = True
		else:
			manifest_refspec = manifest_revision
			manifest_force = False
		self.manifest_repo.push(remote, manifest_refspec, force=manifest_force)
		output.append('manifest branch %s pushed to %s' % (manifest_revision, r['remote']))

		return '\n'.join(output)

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
