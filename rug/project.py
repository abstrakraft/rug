#!/usr/bin/env python
import os
import sys
import xml.dom.minidom

import manifest
import git
import hierarchy
import buffer

class RugError(StandardError):
	pass

class InvalidProjectError(RugError):
	pass

RUG_DIR = '.rug'
#TODO: should this be configurable or in the manifest?
RUG_SHA_RIDER = 'refs/rug/sha_rider'
RUG_DEFAULT_DEFAULT = {'revision': 'master', 'vcs': 'git'}

class Revset(git.Rev):
	def __init__(self, project, name):
		super(Revset, self).__init__(project.manifest_repo, name)

	@classmethod
	def create(cls, repo, dst, src=None):
		return super(Revset, cls).create(repo.manifest_repo, dst, src)

	@classmethod
	def cast(cls, project, revset):
		#TODO: the cast superclass calls are fragile - rework
		if isinstance(revset, git.Rev):
			return cls(project, revset.name)
		else:
			return super(Revset, cls).cast(project, revset)

class Project(object):
	vcs_class = {}
	rev_class = Revset

	def __init__(self, project_dir, output=None):
		if output is None:
			output = buffer.NullBuffer()
		self.output = output

		self.dir = os.path.abspath(project_dir)
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
		self.read_manifest()

	def read_manifest(self):
		'''Project.read_manifest() -- read the manifest file.
Project methods should only call this function if necessary.'''
		(self.remotes, self.repos) = manifest.read(self.manifest_filename, default_default=RUG_DEFAULT_DEFAULT)
		if not self.bare:
			for path in self.repos:
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
	def find_project(cls, project_dir=None, output=None):
		'Project.find_project(project_dir=pwd) -> project -- climb up the directory tree looking for a valid rug project'

		if project_dir == None:
			project_dir = os.getcwd()

		head = project_dir
		while head:
			try:
				return cls(head, output=output)
			except InvalidProjectError:
				if head == os.path.sep:
					head = None
				else:
					(head, tail) = os.path.split(head)

		raise InvalidProjectError('not a valid rug project')

	@classmethod
	def init(cls, project_dir, bare=False, output=None):
		'Project.init -- initialize a new rug repository'

		if output is None:
			output = buffer.NullBuffer()

		if project_dir == None:
			project_dir = '.'

		if cls.valid_project(project_dir):
			raise RugError('%s is an existing rug project' % project_dir)

		if bare:
			rug_dir = project_dir
		else:
			rug_dir = os.path.join(project_dir, RUG_DIR)
		manifest_dir = os.path.join(rug_dir, 'manifest')
		manifest_filename = os.path.join(manifest_dir, 'manifest.xml')

		mr = git.Repo.init(manifest_dir)
		manifest.write(manifest_filename, {}, {}, {})
		mr.add(os.path.basename(manifest_filename))
		mr.commit('Initial commit')

		return cls(project_dir, output=output)

	@classmethod
	def clone(cls, url, project_dir=None, source=None, revset=None, bare=False, output=None):
		'Project.clone -- clone an existing rug repository'

		if output is None:
			output = buffer.NullBuffer()
		#TODO: more output

		#calculate directory
		if project_dir == None:
			basename = os.path.basename(url)
			if len(basename) == 0:
				basename = os.path.basename(url[:-1])
			project_dir = os.path.splitext(basename)[0]
		project_dir = os.path.abspath(project_dir)

		#verify directory doesn't exist
		if os.path.exists(project_dir):
			raise RugError('Directory already exists')

		if bare:
			rug_dir = project_dir
		else:
			rug_dir = os.path.join(project_dir, RUG_DIR)
		manifest_dir = os.path.join(rug_dir, 'manifest')
		manifest_filename = os.path.join(manifest_dir, 'manifest.xml')

		#clone manifest repo into rug directory
		git.Repo.clone(url, repo_dir=manifest_dir, remote=source, rev=revset)

		#verify valid manifest
		if not os.path.exists(manifest_filename):
			raise RugError('invalid manifest repo: no manifest.xml')

		output.append('%s cloned into %s' % (url, project_dir))

		#checkout revset
		p = cls(project_dir, output=output)
		output.append(p.checkout(revset))

		return p

	@classmethod
	def valid_project(cls, project_dir, include_bare=True):
		'Project.valid_project(project_dir) -- verify the minimum qualities necessary to be called a rug project'
		return cls.valid_working_project(project_dir) or include_bare and cls.valid_bare_project(project_dir)

	@classmethod
	def valid_working_project(cls, project_dir):
		manifest_dir = os.path.join(project_dir, RUG_DIR, 'manifest')
		return git.Repo.valid_repo(manifest_dir) \
				and os.path.exists(os.path.join(manifest_dir, 'manifest.xml'))

	@classmethod
	def valid_bare_project(cls, project_dir):
		manifest_dir = os.path.join(project_dir, 'manifest')
		return git.Repo.valid_repo(manifest_dir) \
			and os.path.exists(os.path.join(manifest_dir, 'manifest.xml'))

	def get_branch_names(self, r):
		revision = r.get('revision', 'HEAD')
		repo = r['repo']
		if revision == 'HEAD':
			start = len('refs/remotes/%s/' % r['remote'])
			revision = repo.symbolic_ref('refs/remotes/%s/HEAD' % r['remote'])[start:]
		ret = {}
		if repo.valid_sha(revision):
			#TODO: rethink how this works for sha repos
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = revision
			ret['rug'] = 'refs/rug/heads/%s/%s/sha/rug_index' % (self.revset().get_short_name(), r['remote'])
			ret['rug_index'] = 'refs/rug/rug_index'
			ret['bookmark'] = 'refs/rug/bookmarks/%s/%s/sha/bookmark' % (self.revset().get_short_name(), r['remote'])
			ret['bookmark_index'] = 'refs/rug/bookmark_index'
			ret['remote'] = revision
		else:
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = 'refs/heads/%s' % revision
			ret['rug'] = 'refs/rug/heads/%s/%s/%s' % (self.revset().get_short_name(), r['remote'], revision)
			ret['rug_index'] = 'refs/rug/rug_index'
			ret['bookmark'] = 'refs/rug/bookmarks/%s/%s/%s' % (self.revset().get_short_name(), r['remote'], revision)
			ret['bookmark_index'] = 'refs/rug/bookmark_index'
			ret['remote'] = '%s/%s' % (r['remote'], revision)

		return ret

	def source_list(self):
		return self.manifest_repo.remote_list()

	def source_add(self, source, url):
		return self.manifest_repo.remote_add(source, url)

	def source_set_url(self, source, url):
		return self.manifest_repo.remote_set_url(source, url)

	def source_set_head(self, source):
		return self.manifest_repo.remote_set_head(source)

	def revset(self):
		'return the current revset'
		return Revset.cast(self, self.manifest_repo.head())

	def revset_list(self):
		'return the list of available revsets'
		#TODO: refs or branches?
		return map(Revset, self.manifest_repo.ref_list())

	def revset_create(self, dst, src=None):
		'create a new revset'
		self.manifest_repo.branch_create(dst, src)

	def revset_delete(self, dst, force=False):
		'delete a revset'
		self.manifest_repo.branch_delete(dst, force)

	def status(self, porcelain=True):
		#TODO: return objects or text?
		#TODO: could add manifest status
		if self.bare:
			raise NotImplementedError('status not implemented for bare projects')

		#TODO: think through this

		if porcelain:
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
		else:
			stat = ['On revset %s:' % self.revset().get_short_name()]
			stat.append('manifest diff:')
			stat.extend(map(lambda line: '\t' + line, self.manifest_repo.diff().split('\n')))
			for r in self.repos.values():
				repo = r['repo']
				if repo is None:
					stat.append('repo %s missing' % r['path'])
				else:
					stat.append('repo %s:' % r['path'])
					stat.extend(map(lambda line: '\t' + line, r['repo'].status(porcelain=False).split('\n')))

		return '\n'.join(stat)

	def dirty(self):
		#TODO: currently, "dirty" is defined as "would commit -a do anything"
		#this seems to work, but needs further consideration
		dirty_repos = False
		for r in self.repos.values():
			branches = self.get_branch_names(r)
			repo = r['repo']
			if (repo is None) or repo.valid_rev(branches['rug_index']):
				dirty_repos = True
				break

		return dirty_repos or self.manifest_repo.dirty()

	def remote_list(self):
		return self.remotes.keys()

	def remote_add(self, remote, fetch):
		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		if not remotes.has_key(remote):
			remotes[remote] = {'name':remote}
		remotes[remote]['fetch'] = fetch
		manifest.write(self.manifest_filename, remotes, repos, default)
		self.read_manifest()

		self.output.append('remote %s added' % remote)

	def checkout(self, revset=None):
		'check out a revset'

		#Checkout manifest manifest
		if revset is None:
			revset = self.revset()
		revset = Revset.cast(self, revset)
		#Always throw away local rug changes - uncommitted changes to the manifest.xml file are lost
		self.manifest_repo.checkout(revset, force=True)

		#reread manifest
		self.read_manifest()

		if not self.bare:
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

					branches = self.get_branch_names(r)

					#create rug and bookmark branches if they don't exist
					#branches are fully qualified ('refs/...') branch names, so use update_ref
					#instead of create_branch
					for b in ['rug', 'bookmark']:
						if not repo.valid_rev(branches[b]):
							repo.update_ref(branches[b], branches['remote'])

					for b in ['rug_index', 'bookmark_index']:
						if repo.valid_rev(branches[b]):
							repo.delete_ref(branches[b])

					#create and checkout the live branch
					repo.update_ref(branches['live_plumbing'], branches['rug'])
					repo.checkout(branches['live_porcelain'])

		self.output.append('revset %s checked out' % revset.get_short_name())

	def create_repo(self, r, sub_repos):
		if self.bare:
			raise RugError('Invalid operation for bare project')
		abs_path = os.path.abspath(os.path.join(self.dir, r['path']))
		url = self.remotes[r['remote']]['fetch'] + '/' + r['name']
		R = self.vcs_class[r['vcs']]
		repo = R.clone(url, repo_dir=abs_path, remote=r['remote'], rev=r.get('revision', None))
		if r['path'] == '.':
			repo.add_ignore(RUG_DIR)
		for sr in sub_repos:
			repo.add_ignore(os.path.relpath(sr, r['path']))
		r['repo'] = repo
		branches = self.get_branch_names(r)
		for b in ['live_plumbing', 'rug', 'bookmark']:
			repo.update_ref(branches[b], branches['remote'])

		repo.checkout(branches['live_porcelain'])

	def fetch(self, source=None, repos=None):
		self.manifest_repo.fetch(source)

		if not self.bare:
			if repos is None:
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

		if repos is None:
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
				branches = self.get_branch_names(r)
				#We don't touch the bookmark branch here - we refer to bookmark index branch if it exists,
				#or bookmark branch if not, and update the bookmark index branch if necessary.  Commit updates
				#bookmark branch and removes bookmark index
				if repo.valid_rev(branches['bookmark_index']):
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

	def add(self, path, name=None, remote=None, rev=None, vcs=None, use_sha=None):
		#TODO:handle lists of dirs
		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		lookup_default = {}
		lookup_default.update(RUG_DEFAULT_DEFAULT)
		lookup_default.update(default)

		update_rug_branch = False

		r = self.repos.get(path, None)
		if r is None:
			# Verify inputs
			if name is None:
				raise RugError('new repos must specify a name')
			if remote is None:
				raise RugError('new repos must specify a remote')
			if self.bare:
				if rev is None:
					raise RugError('new repos in bare projects must specify a rev')
				if vcs is None:
					raise RugError('new repos in bare projects must specify a vcs')

			#Find vcs if not specified, and create repo object
			abs_path = os.path.join(self.dir, path)
			if vcs is None:
				repo = None
				#TODO: rug needs to take priority here, as rug repos with sub-repos at '.'
				#will look like the sub-repo vcs as well as a rug repo
				#(but not if the path of the sub-repo is '.')
				for (try_vcs, R) in self.vcs_class.items():
					if R.valid_repo(abs_path):
						repo = R(abs_path)
						vcs = try_vcs
						break
				if repo is None:
					raise RugError('unrecognized repo %s' % path)
			else:
				repo = vcs_class[vcs](abs_path)

			#Add the repo
			repos[path] = {'path': path}

			#TODO: we don't know if the remote even exists yet, so can't set up all branches
			#logic elsewhere should be able to handle this possibility (remote & bookmark branches don't exist)
			if not self.bare:
				update_rug_branch = True
		else:
			repo = r['repo']

			if remote is not None:
				update_rug_branch = True

		if use_sha is None:
			use_sha = repo.valid_sha(r.get('revision', lookup_default['revision']))

		#Get the rev
		if rev is None:
			rev = repo.head()
		else:
			rev = repo.rev_class.cast(repo, rev)
		if use_sha:
			rev = repo.rev_class(repo, rev.get_sha())
		revision = rev.get_short_name()

		#Update repo properties
		for p in ['revision', 'name', 'remote', 'vcs']:
			pval = eval(p)
			if (pval is not None) and (pval != lookup_default.get(p)):
				repos[path][p] = pval

		#Write the manifest and reload repos
		manifest.write(self.manifest_filename, remotes, repos, default)
		self.read_manifest()
		r = self.repos[path]
		repo = r['repo']
		branches = self.get_branch_names(r)

		#Update rug_index
		repo.update_ref(branches['rug_index'], rev)

		#If this is a new repo, set the rug branch
		if update_rug_branch:
			repo.update_ref(branches['rug'], rev)

		self.output.append("%s added to manifest" % path)

	def commit(self, message=None, all=False):
		if (message is None) and all:
			raise RugError('commit message required for -a')

		if not self.bare:
			for r in self.repos.values():
				repo = r['repo']
				if all:
					if repo.dirty():
						repo.commit(message, all=True)
					#TODO: test for need
					self.add(r['path'])
					r = self.repos[r['path']]
				branches = self.get_branch_names(r)
				if repo.valid_rev(branches['rug_index']):
					repo.update_ref(branches['rug'], branches['rug_index'])
					repo.delete_ref(branches['rug_index'])

				if repo.valid_rev(branches['bookmark_index']):
					repo.update_ref(branches['bookmark'], branches['bookmark_index'])
					repo.delete_ref(branches['bookmark_index'])

		#TODO: what about untracked files?
		if self.manifest_repo.dirty():
			if message is None:
				raise RugError('commit message required')
			self.manifest_repo.commit(message, all=True)

	#TODO: remove this quick hack
	def test_publish(self, remote=None):
		return self.publish(remote, test=True)

	def publish(self, source=None, test=False):
		if source is None:
			source = 'origin'
		if not source in self.source_list():
			raise RugError('unrecognized source %s' % source)

		#TODO: This may not be the best way to do this, but we need the manifest
		#as of the last commit.
		do_manifest_stash_pop = False
		if self.manifest_repo.dirty():
			do_manifest_stash_pop = True
			self.manifest_repo.stash()
			self.read_manifest()

		#TODO: use manifest.read with apply_default=False
		error = []

		#Verify that we can push to all unpublished remotes
		ready = True
		repo_updates = []

		if not self.bare:
			for r in self.repos.values():
				repo = r['repo']
				branches = self.get_branch_names(r)
				update_repo = False
				if not repo.valid_rev(branches['bookmark']):
					update_repo = True
				else:
					rug_rev = repo.rev_class(repo, branches['rug'])
					bookmark_rev = repo.rev_class(repo, branches['bookmark'])
					update_repo = rug_rev.get_sha() != bookmark_rev.get_sha()
				if update_repo:
					#TODO: verify correctness & consistency of path functions/formats throughout rug

					if repo.valid_sha(r['revision']):
						#TODO: PROBLEM: branches pushed as sha_riders may not have heads associated with them,
						#which means that clones won't pull them down
						refspec = '%s:refs/heads/%s' % (r['revision'], RUG_SHA_RIDER)
						force = True
					else:
						refspec = '%s:refs/heads/%s' % (branches['rug'], r['revision'])
						force = False
					repo_updates.append((r, refspec, force))
					if not repo.test_push(r['remote'], refspec, force=force):
						error.append('%s: %s cannot be pushed to %s' % (r['name'], r['revision'], r['remote']))
						ready = False

		#Verify that we can push to manifest repo
		#TODO: We don't always need to push manifest repo
		manifest_revision = self.revset()
		if manifest_revision.is_sha():
			manifest_refspec = '%s:refs/heads/%s' % (manifest_revision.get_sha(), RUG_SHA_RIDER)
			manifest_force = True
		else:
			manifest_refspec = manifest_revision.get_short_name()
			manifest_force = False
		if not self.manifest_repo.test_push(source, manifest_refspec, force=manifest_force):
			error.append('manifest branch %s cannot be pushed to %s' % (manifest_revision.get_short_name(), source))
			ready = False

		if test:
			return ready

		#Error if we can't publish anything
		if not ready:
			print repo_updates
			raise RugError('\n'.join(error))

		#Push unpublished remotes
		for (r, refspec, force) in repo_updates:
			repo = r['repo']
			repo.push(r['remote'], refspec, force)
			branches = self.get_branch_names(r)
			repo.update_ref(branches['bookmark'], branches['rug'])
			self.output.append('%s: pushed %s to %s' % (r['name'], r['revision'], r['remote']))

		#Push manifest
		#TODO: we've taken steps to predict errors, but failure can still happen.  Need to
		#leave the repo in a consistent state if that happens
		self.manifest_repo.push(source, manifest_refspec, force=manifest_force)
		self.output.append('manifest branch %s pushed to %s' % (manifest_revision.get_short_name(), source))

		if do_manifest_stash_pop:
			self.manifest_repo.stash_pop()
			self.read_manifest()

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
