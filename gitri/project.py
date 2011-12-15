#!/usr/bin/env python
import os
import sys
import xml.dom.minidom

import manifest
import git
from repo import Repo

class GitriError(StandardError):
	pass

class InvalidProjectError(GitriError):
	pass

GITRI_DIR = '.gitri'
#TODO: should this be configurable or in the manifest?
GITRI_SHA_RIDER = 'gitri/sha_rider'

class Project(object):
	vcs_constructors = {
		'git': git.Repo,
		'gitri': Repo,
	}

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
		'''Project.read_manifest() -- read the manifest file.
Project methods should only call this function if necessary.'''
		default_default = {'vcs': 'git'}
		(self.remotes, self.repos) = manifest.read(os.path.join(self.manifest_dir, 'manifest.xml'),
			default_default=default_default)

	def load_repos(self, repos=None):
		'''Project.load_repos(repos=self.repos) -- load repo objects for repos.
Project.read_manifest should be called prior to calling this function.
Project methods should only call this function if necessary.
Loads all repos by default, or those repos specified in the repos argument, which may be a list or a dictionary.'''

		if repos is None:
			repos = self.repos

		for path in repos:
			abs_path = os.path.abspath(os.path.join(self.dir, path))
			R = self.vcs_constructors[self.repos[path]['vcs']]
			if R.valid_repo(abs_path):
				self.repos[path]['repo'] = R(abs_path)
			else:
				self.repos[path]['repo'] = None

	@classmethod
	def find_project(cls, dir = None):
		'Project.find_project(dir=pwd) -> project -- climb up the directory tree looking for a valid gitri project'

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
	def clone(cls, url, dir=None, revset=None):
		'Project.clone -- clone an existing gitri repository'

		#TODO: more output

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

		output = ['%s cloned into %s' % (url, dir)]

		#checkout revset
		p = cls(dir)
		output.append(p.checkout())

		return '\n'.join(output)

	@classmethod
	def valid_project(cls, dir):
		'Project.valid_project(dir) -- verify the minimum qualities necessary to be called a gitri project'
		manifest_dir = os.path.join(dir, GITRI_DIR, 'manifest')
		return git.Repo.valid_repo(manifest_dir) and \
			os.path.exists(os.path.join(manifest_dir, 'manifest.xml'))

	def get_branches(self, r):
		revision = r.get('revision', 'HEAD')
		repo = r['repo']
		if revision == 'HEAD':
			start = len('refs/remotes/%s/' % r['remote'])
			revision = repo.symbolic_ref('refs/remotes/%s/HEAD' % r['remote'])[start:]
		ret = {}
		if repo.valid_sha(revision):
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = revision
			ret['gitri'] = revision
			ret['bookmark'] = revision
			ret['bookmark_index'] = revision
			ret['remote'] = revision
		else:
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = 'refs/heads/%s' % revision
			ret['gitri'] = 'refs/gitri/heads/%s/%s/%s' % (self.revset(), r['remote'], revision)
			ret['bookmark'] = 'refs/gitri/bookmarks/%s/%s/%s' % (self.revset(), r['remote'], revision)
			ret['bookmark_index'] = 'refs/gitri/bookmark_index'
			ret['remote'] = '%s/%s' % (r['remote'], revision)

		return ret

	def revset(self):
		'return the name of the current revset'
		return self.manifest_repo.head()

	def revset_create(self, dst, src=None):
		'create a new revset'
		self.manifest_repo.branch_create(dst, src)

	def revset_delete(self, dst, force=False):
		'delete a revset'
		self.manifest_repo.branch_delete(dst, force)

	def status(self):
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

	def checkout(self, revset=None):
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
				self.create_repo(r)
			else:
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

				branches = self.get_branches(r)

				#create gitri and bookmark branches if they don't exist
				#branches are fully qualified ('refs/...') branch names, so use update_ref
				#instead of create_branch
				for b in ['gitri', 'bookmark']:
					if not repo.valid_ref(branches[b]):
						repo.update_ref(branches[b], branches['remote'])

				#create and checkout the live branch
				repo.update_ref(branches['live_plumbing'], branches['gitri'])
				repo.checkout(branches['live_porcelain'])

		return 'revset %s checked out' % revset

	def create_repo(self, r):
		abs_path = os.path.abspath(os.path.join(self.dir, r['path']))
		url = self.remotes[r['remote']]['fetch'] + '/' + r['name']
		R = self.vcs_constructors[r['vcs']]
		repo = R.clone(url, dir=abs_path, remote=r['remote'], rev=r.get('revision', None))
		r['repo'] = repo
		branches = self.get_branches(r)
		for b in ['live_plumbing', 'gitri', 'bookmark']:
			repo.update_ref(branches[b], branches['remote'])

		repo.checkout(branches['live_porcelain'])

	def fetch(self, repos=None):
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

	def update(self, repos=None):
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
				branches = self.get_branches(r)
				#We don't touch the bookmark branch here - we refer to bookmark index branch if it exists,
				#or bookmark branch if not, and update the bookmark index branch if necessary.  Commit updates
				#bookmark branch and removes bookmark index
				if repo.valid_ref(branches['bookmark_index']):
					current_bookmark = branches['bookmark_index']
				else:
					current_bookmark = branches['bookmark']
				#Check if there are no changes
				if repo.rev_parse(repo.head()) == repo.rev_parse(branches['remote']):
					output.append('%s is up to date with upstream repo: no change' % r['name'])
				elif repo.is_descendant(branches['remote']):
					output.append('%s is ahead of upstream repo: no change' % r['name'])
				#Fast-Forward if we can
				elif repo.can_fastforward(branches['remote']):
					output.append('%s is being fast-forward to upstream repo' % r['name'])
					repo.merge(branches['remote'])
					repo.update_ref(branches['bookmark_index'], branches['remote'])
				#otherwise rebase/merge local work
				elif repo.is_descendant(bookmark_branch):
					if repo.dirty():
						#TODO: option to stash, rebase, then reapply?
						output.append('%s has local uncommitted changes and cannot be rebased. Skipping this repo.' % r['name'])
					else:
						#TODO: option to merge instead of rebase
						#TODO: handle merge/rebase conflicts
						#TODO: remember if we're in a conflict state
						output.append('%s is being rebased onto upstream repo' % r['name'])
						[ret,out,err] = repo.rebase(bookmark_branch, onto=branches['remote'])
						if ret:
							output.append(out)
						else:
							repo.update_ref(branches['bookmark_index'], branches['remote'])
				#Fail
				elif repo.head() != branches['gitri']:
					output.append('%s has changed branches and cannot be safely updated. Skipping this repo.' % r['name'])
				else:
					#Weird stuff has happened - right branch, wrong relationship to bookmark
					output.append('The current branch in %s has been in altered in an unusal way and must be manually updated.' % r['name'])
			else:
				self.create_repo(r)

		return '\n'.join(output)

	def add(self, dir):
		#TODO:options and better logic to add shas vs branch names
		#TODO:handle lists of dirs
		self.read_manifest()

		abs_path = os.path.abspath(dir)
		path = os.path.relpath(abs_path, self.dir)
		r = self.repos.get(path, None)
		if r is None:
			#TODO: handle new repos
			raise GitriError('unrecognized repo %s' % dir)
		else:
			self.load_repos([path])
			#TODO: check for errors in load_repos
			repo = r['repo']
			head = repo.head()
			#TODO: revise logic here to take care of shas/branch names, branches that have changed sha
			if repo.valid_sha(head):
				if r['revision'] == head:
					raise GitriError('no change to repo %s' % dir)
			else:
				branches = self.get_branches(r)
				if repo.rev_parse(branches['gitri']) == repo.rev_parse(head):
					raise GitriError('no change to repo %s' % dir)

			filename = os.path.join(self.manifest_dir, 'manifest.xml')
			(remotes, repos, default) = manifest.read(filename, apply_default=False)
			#TODO: don't specify revision if it is the default and hasn't changed
			repos[path]['revision'] = head
			repos[path]['unpublished'] = 'true'
			manifest.write(filename, remotes, repos, default)

			return "%s added to manifest" % path

	def commit(self, message):
		self.read_manifest()
		self.load_repos()

		#TODO: currently, if a branch is added, we commit the branch as it exists at commit time
		#rather than add time.  Correct operation should be determined.

		if message is None:
			message = ""
		self.manifest_repo.commit(message, all=True)

		for r in self.repos.values():
			repo = r['repo']
			branches = self.get_branches(r)
			repo.update_ref(branches['gitri'], branches['live_plumbing'])

			if repo.valid_ref(branches['bookmark_index'], include_sha=False):
				repo.update_ref(branches['bookmark'], branches['bookmark_index'])
				repo.branch_delete(branches['bookmark_index'])

	#TODO: remove this quick hack
	def test_publish(self, remote=None):
		return self.publish(remote, test=True)

	def publish(self, remote=None, test=False):
		if remote is None:
			remote = 'origin'
		if not remote in self.manifest_repo.remote_list():
			raise GitriError('unrecognized remote %s' % remote)

		#TODO: use manifest.read with apply_default=False
		self.read_manifest()

		error = []
		output = []

		#Verify that we can push to all unpublished remotes
		ready = True
		unpub_repos = []
		for r in self.repos.values():
			if r.get('unpublished', False):
				#TODO: verify correctness & consistency of path functions/formats throughout gitri
				self.load_repos([r['path']])
				repo = r['repo']

				if repo.valid_sha(r['revision']):
					#TODO: PROBLEM: branches pushed as sha_riders may not have heads associated with them,
					#which means that clones won't pull them down
					refspec = '%s:refs/%s' % (r['revision'], GITRI_SHA_RIDER)
					force = True
				else:
					refspec = r['revision']
					force = False
				#TODO: repo is now in r
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

		if test:
			return ready

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
		#TODO: think about interaction between commit and publish - should commit be required?
		#TODO:input commit message
		#TODO: we've taken steps to predict errors, but failure can still happen.  Need to
		#leave the repo in a consistent state if that happens
		if self.manifest_repo.dirty():
			self.commit(message="Gitri publish commit")
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
