#!/usr/bin/env python
import os
import sys
import xml.dom.minidom

import manifest
import git
import hierarchy

class RugError(StandardError):
	pass

class InvalidProjectError(RugError):
	pass

RUG_DIR = '.rug'
#TODO: should this be configurable or in the manifest?
RUG_SHA_RIDER = 'rug/sha_rider'
RUG_DEFAULT_DEFAULT = {'revision': 'master', 'vcs': 'git'}

class Project(object):
	vcs_class = {}

	def __init__(self, dir):
		self.dir = os.path.abspath(dir)
		#Verify validity
		if not self.valid_project(self.dir):
			raise InvalidProjectError('not a valid rug project')

		#Decide if bare
		self.bare = self.valid_bare_project(self.dir)

		#Create convenient properties
		if self.bare:
			self.rug_dir = self.dir
		else:
			self.rug_dir = os.path.join(self.dir, RUG_DIR)
		self.manifest_dir = os.path.join(self.rug_dir, 'manifest')
		self.manifest_filename = os.path.join(self.manifest_dir, 'manifest.xml')
		self.manifest_repo = git.Repo(self.manifest_dir)

	def read_manifest(self):
		'''Project.read_manifest() -- read the manifest file.
Project methods should only call this function if necessary.'''
		(self.remotes, self.repos) = manifest.read(self.manifest_filename, default_default=RUG_DEFAULT_DEFAULT)

	def load_repos(self, repos=None):
		'''Project.load_repos(repos=self.repos) -- load repo objects for repos.
Project.read_manifest should be called prior to calling this function.
Project methods should only call this function if necessary.
Loads all repos by default, or those repos specified in the repos argument, which may be a list or a dictionary.'''
		if self.bare:
			raise RugError('Invalid operation for bare project')

		if repos is None:
			repos = self.repos

		for path in repos:
			abs_path = os.path.abspath(os.path.join(self.dir, path))
			R = self.vcs_class[self.repos[path]['vcs']]
			if R.valid_repo(abs_path):
				self.repos[path]['repo'] = R(abs_path)
			else:
				self.repos[path]['repo'] = None

	@classmethod
	def register_vcs(cls, vcs, vcs_class):
		cls.vcs_class[vcs] = vcs_class

	@classmethod
	def find_project(cls, dir = None):
		'Project.find_project(dir=pwd) -> project -- climb up the directory tree looking for a valid rug project'

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

		raise InvalidProjectError('not a valid rug project')

	@classmethod
	def init(cls, dir, bare=False):
		'Project.init -- initialize a new rug repository'

		if dir == None:
			dir = '.'

		if cls.valid_project(dir):
			raise RugError('%s is an existing rug project' % dir)

		if bare:
			rug_dir = dir
		else:
			rug_dir = os.path.join(dir, RUG_DIR)
		manifest_dir = os.path.join(rug_dir, 'manifest')
		manifest_filename = os.path.join(manifest_dir, 'manifest.xml')

		mr = git.Repo.init(manifest_dir)
		manifest.write(manifest_filename, {}, {}, {})
		mr.add(os.path.basename(manifest_filename))
		mr.commit('Initial commit')

		return ''

	@classmethod
	def clone(cls, url, dir=None, remote=None, revset=None, bare=False):
		'Project.clone -- clone an existing rug repository'

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
			raise RugError('Directory already exists')

		if bare:
			rug_dir = dir
		else:
			rug_dir = os.path.join(dir, RUG_DIR)
		manifest_dir = os.path.join(rug_dir, 'manifest')
		manifest_filename = os.path.join(manifest_dir, 'manifest.xml')

		#clone manifest repo into rug directory
		git.Repo.clone(url, dir=manifest_dir, remote=remote, rev=revset)

		#verify valid manifest
		if not os.path.exists(manifest_filename):
			raise RugError('invalid manifest repo: no manifest.xml')

		output = ['%s cloned into %s' % (url, dir)]

		#checkout revset
		p = cls(dir)
		output.append(p.checkout())

		return '\n'.join(output)

	@classmethod
	def valid_project(cls, dir, include_bare=True):
		'Project.valid_project(dir) -- verify the minimum qualities necessary to be called a rug project'
		return cls.valid_working_project(dir) or include_bare and cls.valid_bare_project(dir)

	@classmethod
	def valid_working_project(cls, dir):
		manifest_dir = os.path.join(dir, RUG_DIR, 'manifest')
		return git.Repo.valid_repo(manifest_dir) \
				and os.path.exists(os.path.join(manifest_dir, 'manifest.xml'))

	@classmethod
	def valid_bare_project(cls, dir):
		manifest_dir = os.path.join(dir, 'manifest')
		return git.Repo.valid_repo(manifest_dir) \
			and os.path.exists(os.path.join(manifest_dir, 'manifest.xml'))

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
			ret['rug'] = revision
			ret['bookmark'] = revision
			ret['bookmark_index'] = revision
			ret['remote'] = revision
		else:
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = 'refs/heads/%s' % revision
			ret['rug'] = 'refs/rug/heads/%s/%s/%s' % (self.revset(), r['remote'], revision)
			ret['bookmark'] = 'refs/rug/bookmarks/%s/%s/%s' % (self.revset(), r['remote'], revision)
			ret['bookmark_index'] = 'refs/rug/bookmark_index'
			ret['remote'] = '%s/%s' % (r['remote'], revision)

		return ret

	def source_list(self):
		return self.manifest_repo.remote_list()

	def source_add(self, remote, url):
		return self.manifest_repo.remote_add(remote, url)

	def source_set_url(self, remote, url):
		return self.manifest_repo.remote_set_url(remote, url)

	def source_set_head(self, remote):
		return self.manifest_repo.remote_set_head(remote)

	def revset(self):
		'return the name of the current revset'
		return self.manifest_repo.head()

	def revset_list(self):
		'return the list of available revsets'
		#TODO: refs or branches?
		return '\n'.join(self.manifest_repo.ref_list())

	def revset_create(self, dst, src=None):
		'create a new revset'
		self.manifest_repo.branch_create(dst, src)

	def revset_delete(self, dst, force=False):
		'delete a revset'
		self.manifest_repo.branch_delete(dst, force)

	def status(self, porcelain=True):
		#TODO: could add manifest status
		if self.bare:
			raise NotImplementedError('status not implemented for bare projects')

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
					stat.extend(['%s\t%s\t%s' % (s[:2], prefix+s[3:], r['path']) for s in r_stat.split('\n')])
			else:
				stat.append(' D ' + r['path'])

		return '\n'.join(stat)

	def remote_list(self):
		self.read_manifest()

		return '\n'.join(self.remotes.keys())

	def remote_add(self, remote, fetch):
		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		if not remotes.has_key(remote):
			remotes[remote] = {'name':remote}
		remotes[remote]['fetch'] = fetch
		manifest.write(self.manifest_filename, remotes, repos, default)

		return 'remote %s added' % remote

	def checkout(self, revset=None):
		'check out a revset'

		#Checkout manifest manifest
		if revset is None:
			revset = self.revset()
		#Always throw away local rug changes - uncommitted changes to the manifest.xml file are lost
		self.manifest_repo.checkout(revset, force=True)

		#reread manifest
		self.read_manifest()

		if not self.bare:
			self.load_repos()

			sub_repos = hierarchy.hierarchy(self.repos.keys())
			for r in self.repos.values():
				url = self.remotes[r['remote']]['fetch'] + '/' + r['name']

				#if the repo doesn't exist, clone it
				repo = r['repo']
				if not repo:
					self.create_repo(r, sub_repos[r['path']])
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

					#create rug and bookmark branches if they don't exist
					#branches are fully qualified ('refs/...') branch names, so use update_ref
					#instead of create_branch
					for b in ['rug', 'bookmark']:
						if not repo.valid_ref(branches[b]):
							repo.update_ref(branches[b], branches['remote'])

					#create and checkout the live branch
					repo.update_ref(branches['live_plumbing'], branches['rug'])
					repo.checkout(branches['live_porcelain'])

		return 'revset %s checked out' % revset

	def create_repo(self, r, sub_repos):
		if self.bare:
			raise RugError('Invalid operation for bare project')
		abs_path = os.path.abspath(os.path.join(self.dir, r['path']))
		url = self.remotes[r['remote']]['fetch'] + '/' + r['name']
		R = self.vcs_class[r['vcs']]
		repo = R.clone(url, dir=abs_path, remote=r['remote'], rev=r.get('revision', None))
		if r['path'] == '.':
			repo.add_ignore(RUG_DIR)
		for sr in sub_repos:
			repo.add_ignore(os.path.relpath(sr, r['path']))
		r['repo'] = repo
		branches = self.get_branches(r)
		for b in ['live_plumbing', 'rug', 'bookmark']:
			repo.update_ref(branches[b], branches['remote'])

		repo.checkout(branches['live_porcelain'])

	def fetch(self, repos=None):
		self.read_manifest()

		self.manifest_repo.fetch()

		if not self.bare:
			if repos is None:
				self.load_repos()
				repos = self.repos.values()
			else:
				#TODO: turn list of strings into repos
				pass

			for r in repos:
				repo = r['repo']
				if repo:
					repo.fetch(r['remote'])
					repo.remote_set_head(r['remote'])

		#TODO:output

	def update(self, repos=None):
		raise NotImplementedError('Update not yet implemented')

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

		sub_repos = hierarchy.hierarchy(self.repos.keys())
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
				elif repo.head() != branches['rug']:
					output.append('%s has changed branches and cannot be safely updated. Skipping this repo.' % r['name'])
				else:
					#Weird stuff has happened - right branch, wrong relationship to bookmark
					output.append('The current branch in %s has been in altered in an unusal way and must be manually updated.' % r['name'])
			else:
				self.create_repo(r, sub_repos[r['path']])

		return '\n'.join(output)

	def add(self, dir, name=None, remote=None):
		if self.bare:
			raise NotImplementedError('add not yet implemented for bare projects')
		#TODO:options and better logic to add shas vs branch names
		#TODO:handle lists of dirs
		self.read_manifest()

		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)

		abs_path = os.path.abspath(dir)
		path = os.path.relpath(abs_path, self.dir)
		r = self.repos.get(path, None)
		if r is None:
			if name is None:
				raise RugError('new repos must specify a name')
			repo = None
			for (vcs, R) in self.vcs_class.items():
				if R.valid_repo(path):
					repo = R(path)
					break
			if repo is None:
				raise RugError('unrecognized repo %s' % dir)
			else:
				repos[path] = {'name': name, 'path': path}
				head = repo.head()
				if head != default.get('revision'):
					repos[path]['revision'] = head
				if (remote is not None) and (remote != default.get('remote')):
					repos[path]['remote'] = remote

				repos[path]['unpublished'] = 'true'
		else:
			self.load_repos([path])
			#TODO: check for errors in load_repos
			repo = r['repo']
			head = repo.head()
			#TODO: revise logic here to take care of shas/branch names, branches that have changed sha
			if repo.valid_sha(head):
				if r['revision'] == head:
					raise RugError('no change to repo %s' % dir)
			else:
				branches = self.get_branches(r)
				if repo.rev_parse(branches['rug']) == repo.rev_parse(head):
					raise RugError('no change to repo %s' % dir)

			if repos[path].has_key('revision') or (default.get('revision') != head):
				repos[path]['revision'] = head
			repos[path]['unpublished'] = 'true'

		manifest.write(self.manifest_filename, remotes, repos, default)

		return "%s added to manifest" % path

	def commit(self, message):
		self.read_manifest()

		#TODO: currently, if a branch is added, we commit the branch as it exists at commit time
		#rather than add time.  Correct operation should be determined.

		if message is None:
			message = ""
		#TODO: what about untracked files?
		if self.manifest_repo.dirty():
			self.manifest_repo.commit(message, all=True)

		if not self.bare:
			self.load_repos()
			for r in self.repos.values():
				repo = r['repo']
				branches = self.get_branches(r)
				repo.update_ref(branches['rug'], branches['live_plumbing'])

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
			raise RugError('unrecognized remote %s' % remote)

		#TODO: use manifest.read with apply_default=False
		self.read_manifest()

		error = []
		output = []

		#Verify that we can push to all unpublished remotes
		ready = True
		unpub_repos = []

		if not self.bare:
			for r in self.repos.values():
				if r.get('unpublished', False):
					#TODO: verify correctness & consistency of path functions/formats throughout rug
					self.load_repos([r['path']])
					repo = r['repo']

					if repo.valid_sha(r['revision']):
						#TODO: PROBLEM: branches pushed as sha_riders may not have heads associated with them,
						#which means that clones won't pull them down
						refspec = '%s:refs/%s' % (r['revision'], RUG_SHA_RIDER)
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
			manifest_refspec = '%s:refs/%s' % (manifest_revision, RUG_SHA_RIDER)
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
			raise RugError('\n'.join(error))

		#Push unpublished remotes
		for (r, repo, refspec, force) in unpub_repos:
			repo.push(r['remote'], refspec, force)
			output.append('%s: pushed %s to %s' % (r['name'], r['revision'], r['remote']))

		#Rewrite manifest
		#TODO: rewrite using manifest.read/write
		unpub_repo_paths = [r['path'] for (r, repo, refspec, force) in unpub_repos]
		manifest = xml.dom.minidom.parse(self.manifest_filename)
		xml_repos = manifest.getElementsByTagName('repo')
		for xr in xml_repos:
			if xr.attributes['path'].value in unpub_repo_paths:
				xr.attributes.removeNamedItem('unpublished')
		file = open(self.manifest_filename, 'w')
		file.write(manifest.toxml()+'\n')
		file.close()

		#Commit and push manifest
		#TODO: think about interaction between commit and publish - should commit be required?
		#TODO: input commit message
		#TODO: we've taken steps to predict errors, but failure can still happen.  Need to
		#leave the repo in a consistent state if that happens
		if self.manifest_repo.dirty():
			self.commit(message="Rug publish commit")
			manifest_revision = self.manifest_repo.head()
			if self.manifest_repo.valid_sha(manifest_revision):
				manifest_refspec = '%s:refs/%s' % (manifest_revision, RUG_SHA_RIDER)
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
	#	rug_branch = 'rug/%s/%s' % (self.origin(), self.revset())
	#
	#	if optlist.has_key('soft'):
	#		mode = git.Repo.SOFT
	#	elif optlist.has_key('mixed'):
	#		mode = git.Repo.MIXED
	#	elif optlist.has_key('hard'):
	#		mode = git.Repo.HARD
	#	
	#	for r in repos:
	#		r.checkout(rug_branch, mode = mode)

Project.register_vcs('git', git.Repo)

#The following code was necessary before manual clone was implemented in order to
#clone into a non-empty directory
#if os.path.exists(path) and (not os.path.isdir(path)):
#	RugError('path %s already exists and is not a directory' % (path,))
#elif os.path.isdir(path) and (os.listdir(path) != []):
#	tmp_path = tempfile(dir='.')
#	#todo: proper path join (detect foreign OS)
#	repo = git.Repo.clone(self.remotes[p['remote']]['fetch'] + '/' + p['name'], tmp_path)
#	#move tmp_path to path
#	#rmdir tmp_path
#else:
#	#path is an empty directory, or doesn't exist
#	#todo: proper path join (detect foreign OS)
