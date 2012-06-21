#!/usr/bin/env python
import os
import sys
import xml.dom.minidom
import config

import manifest
import wrapper
import git
import hierarchy
import output

from rug_common import *

class RugError(StandardError):
	pass

class InvalidProjectError(RugError):
	pass

class Revset(git.Rev):
	@staticmethod
	def find_repo(repo_finder):
		return repo_finder.manifest_repo

class Project(object):
	def __init__(self, project_dir, output_buffer=None):
		if output_buffer is None:
			output_buffer = output.NullOutputBuffer()
		self.output = output_buffer

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
		self.manifest_repo = git.Repo(self.manifest_dir, output_buffer=self.output.spawn('manifest: '))
		self.import_manifest()

	def import_manifest(self):
		'''Project.import_manifest() -- import the manifest file.'''
		(self.remotes, repos) = manifest.read(self.manifest_filename, default_default=RUG_DEFAULT_DEFAULT)
		self.wrappers = {}
		for r in repos.values():
			self.wrappers[r['path']] = wrapper.Wrapper(self, output_buffer=self.output, **r)

	@classmethod
	def find_project(cls, project_dir=None, output_buffer=None):
		'Project.find_project(project_dir=pwd) -> project -- climb up the directory tree looking for a valid rug project'

		if project_dir == None:
			project_dir = os.getcwd()

		head = project_dir
		while head:
			try:
				return cls(head, output_buffer=output_buffer)
			except InvalidProjectError:
				if head == os.path.sep:
					head = None
				else:
					(head, tail) = os.path.split(head)

		raise InvalidProjectError('not a valid rug project')

	@classmethod
	def init(cls, project_dir, bare=False, output_buffer=None):
		'Project.init -- initialize a new rug repository'
		return cls.clone_init(False, project_dir, bare, output_buffer=output_buffer)

	@classmethod
	def clone(cls, url, project_dir=None, source=None, revset=None, bare=False, repo_config=None, output_buffer=None):
		'Project.clone -- clone an existing rug repository'
		return cls.clone_init(True, project_dir, bare, url, source, revset, repo_config, output_buffer)

	@classmethod
	def clone_init(cls, do_clone, project_dir=None, bare=False, url=None, source=None, revset=None, repo_config=None, output_buffer=None):
		if output_buffer is None:
			output_buffer = output.NullOutputBuffer()
		#TODO: more output

		if do_clone:
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
		else: #init
			if project_dir == None:
				project_dir = '.'
			if cls.valid_project(project_dir):
				raise RugError('%s is an existing rug project' % project_dir)

		if bare:
			rug_dir = project_dir
		else:
			rug_dir = os.path.join(project_dir, RUG_DIR)
		os.makedirs(rug_dir)

		config_file = os.path.join(rug_dir, RUG_CONFIG)
		open(config_file, 'w').close()

		manifest_dir = os.path.join(rug_dir, 'manifest')
		manifest_filename = os.path.join(manifest_dir, 'manifest.xml')

		if do_clone:
			#clone manifest repo into rug directory
			candidate_urls = map(lambda c: c % url, RUG_CANDIDATE_TEMPLATES)
			clone_url = None
			for cu in candidate_urls:
				if git.Repo.valid_repo(cu, config=repo_config):
					clone_url = cu
					break
			if clone_url:
				git.Repo.clone(clone_url, repo_dir=manifest_dir, remote=source, rev=revset,
				               config=repo_config, output_buffer=output_buffer.spawn('manifest: '))
			else:
				raise RugError('%s does not seem to be a rug project' % url)

			#verify valid manifest
			if not os.path.exists(manifest_filename):
				raise RugError('invalid manifest repo: no manifest.xml')

			output_buffer.append('%s cloned into %s' % (url, project_dir))

			#checkout revset
			p = cls(project_dir, output_buffer=output_buffer)
			if repo_config is not None:
				for (name, value) in repo_config.items():
					p.set_config(RUG_REPO_CONFIG_SECTION, name, value)
			p.checkout(revset)

			return p
		else: #init
			mr = git.Repo.init(manifest_dir, output_buffer=output_buffer.spawn('manifest: '))
			manifest.write(manifest_filename, {}, {}, {})
			mr.add(os.path.basename(manifest_filename))
			mr.commit('Initial commit')

			return cls(project_dir, output_buffer=output_buffer)

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

	def set_config(self, section, name, value):
		config_file = os.path.join(self.rug_dir, RUG_CONFIG)
		cf = config.ConfigFile.from_path(config_file)
		cf.set(section, name, value)
		cf.to_path(config_file)

	def get_config(self, section, name=None):
		config_file = os.path.join(self.rug_dir, RUG_CONFIG)
		cf = config.ConfigFile.from_path(config_file)
		return cf.get(section, name)

	def get_rug_config(self):
		try:
			return self.get_config(RUG_REPO_CONFIG_SECTION)
		except KeyError:
			return None

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
		#TODO: currently returns "HEAD" for detached heads
		return Revset.cast(self, self.manifest_repo.head())

	def revset_list(self):
		'return the list of available revsets'
		#TODO: refs or branches?
		return map(lambda rs: Revset.cast(self, rs), self.manifest_repo.ref_list())

	def revset_create(self, dst, src=None):
		'create a new revset'
		self.manifest_repo.branch_create(dst, src)

	def revset_delete(self, dst, force=False):
		'delete a revset'
		self.manifest_repo.branch_delete(dst, force)

	def status(self, porcelain=True, recursive=True):
		#TODO: return objects or text?
		#TODO: could add manifest status
		if self.bare:
			raise NotImplementedError('status not implemented for bare projects')

		#TODO: think through this

		#Committed revset info
		manifest_blob_id = self.manifest_repo.get_blob_id('manifest.xml')
		commit_repos = manifest.read_from_string(
				self.manifest_repo.show(manifest_blob_id),
				default_default=RUG_DEFAULT_DEFAULT
			)[1]

		if porcelain:
			ret = {}
			for r in self.wrappers.values():
				ret[r.path] = r.status(commit_repos.get(r.path), porcelain=porcelain, recursive=recursive)
			#TODO: stuff in commit_r but not in self.wrappers should be 'D?'
		else:
			ret = ['On revset %s:' % self.revset().get_short_name()]
			diff = self.manifest_repo.diff()
			if diff:
				ret.append('manifest diff:')
				ret.extend(map(lambda line: '\t' + line, self.manifest_repo.diff().split('\n')))
			for r in self.wrappers.values():
				stat = r.status(commit_repos.get(r.path), porcelain=porcelain, recursive=recursive)
				if recursive and stat[1] is not None:
					ret.append('repo %s (%s):' % (r.path, stat[0]))
					ret.extend(map(lambda line: '\t' + line, stat[1].split('\n')))
				else:
					ret.append('repo %s (%s)' % (r.path, stat))
			#TODO: stuff in commit_r but not in self.wrappers should be 'D?'
			ret = '\n'.join(ret)

		return ret

	def dirty(self):
		#currently, "dirty" is defined as "would commit -a do anything"
		if self.manifest_repo.dirty():
			return True
		else:
			for r in self.wrappers.values():
				if r.dirty():
					return True
		return False

	def remote_list(self):
		return self.remotes.keys()

	def remote_add(self, remote, fetch):
		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		if remote not in remotes:
			remotes[remote] = {'name':remote}
		remotes[remote]['fetch'] = fetch
		manifest.write(self.manifest_filename, remotes, repos, default)
		self.import_manifest()

		self.output.append('remote %s added' % remote)

	def default_add(self, field, value):
		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		default[field] = value
		manifest.write(self.manifest_filename, remotes, repos, default)
		self.import_manifest()

		self.output.append('default added: %s=%s' % (field, value))

	def checkout(self, revset=None):
		'check out a revset'

		#Checkout manifest manifest
		if revset is None:
			revset = self.revset()
		revset = Revset.cast(self, revset)
		#Always throw away local rug changes - uncommitted changes to the manifest.xml file are lost
		self.manifest_repo.checkout(revset, force=True)

		#reread manifest
		self.import_manifest()

		if not self.bare:
			for r in self.wrappers.values():
				r.checkout()

		self.output.append('revset %s checked out' % revset.get_short_name())

	def merge(self, revset, message=None, do_merge_default=False):
		pass

	def merge_manifest(self, revset, message=None, do_merge_default=False, remotes=None, paths=None):
		if remotes is None:
			remotes = []
		elif isinstance(remotes, basestring):
			remotes = [remotes]

		if paths is None:
			paths = []
		elif isinstance(paths, basestring):
			paths = [paths]

		(head_remotes, head_repos, head_default) = manifest.read(self.manifest_filename, apply_default=False)

		revset_manifest_blob_id = self.manifest_repo.get_blob_id('manifest.xml', rev)
		#If we're not merging defaults, we need to apply defaults, as differences in defaults
		#can result in effective differences in the remote/path
		#If we are merging defaults, this can't happen, so don't apply
		if do_merge_default:
			(merge_remotes, merge_repos, merge_default) = manifest.read_from_string(
					self.manifest_repo.show(revset_manifest_blob_id),
					apply_default=False
				)
			head_default.update(merge_default)
		else:
			(merge_remotes, merge_repos) = manifest.read_from_string(self.manifest_repo.show(revset_manifest_blob_id))

		lookup_default = {}
		lookup_default.update(RUG_DEFAULT_DEFAULT)
		lookup_default.update(head_default)

		for remote in remotes:
			if remote in head_remotes:
				r = head_remotes[remote]
			else:
				r = {}
				head_remotes[remote] = r
			r.update(merge_remotes[remote])

		for path in paths:
			if path in head_repos:
				r = head_repos[path]
			else:
				r = {}
				head_repos[path] = r
			r.update(merge_repos[path])
			#TODO: refine this logic - there may be cases where a default is explicitly
			#specified, and we may want to keep that specification.
			for (k,v) in default.items():
				if r[k] == v:
					del r[k]

		manifest.write(self.manifest_filename, head_remotes, head_repos, head_default)
		if self.manifest_repo.dirty():
			if message is None:
				message = 'merged from %s' % revset
			self.manifest_repo.commit(message, all=True)
		else:
			self.output.append('Nothing to merge')

		#no need to import_manifest here - checkout will do this
		self.checkout()

	def merge_revision(self, revset, paths=None):
		if self.bare:
			raise RugError('Invalid operation for bare project')

		if paths is None:
			paths = []
		elif isinstance(paths, basestring):
			paths = [paths]

		#(remotes, repos) = manifest.read(self.manifest_filename,
		#		apply_default=True,
		#		default_default=RUG_DEFAULT_DEFAULT)

		revset_manifest_blob_id = self.manifest_repo.get_blob_id('manifest.xml', rev)
		(merge_remotes, merge_repos) = manifest.read_from_string(
				self.manifest_repo.show(revset_manifest_blob_id),
				apply_default=True,
				default_default=RUG_DEFAULT_DEFAULT)

		for path in paths:
			r = self.repos[path]
			repo = r['repo']
			merge_r = rev_repos[path]
			#Verify and fetch the rev remote
			self.verify_remote(merge_r, merge_remotes)
			repo.fetch(merge_r['remote'])

			#Figure out what the remote branch name is
			#If the rev is a sha, it's just rev, if a branch name, it's remote/rev
			rev_class = self.vcs_class[rev_r['vcs']].rev_class
			try:
				merge_rev = rev_class(repo, merge_r['rev'])
				is_sha = merge_rev.is_sha()
			except UnknownRevisionError:
				is_sha = False
			if not is_sha:
				merge_rev = rev_class(repo, '%s/%s' % (merge_r['remote'], merge_r['rev']))

			#Do the merge
			#TODO: what to do on conflict!?
			repo.merge(merge_rev)

	def fetch(self, source=None, paths=None):
		self.manifest_repo.fetch(source)

		if not self.bare:
			if paths is None:
				paths = self.wrappers.keys()

			for r in [self.repos[p] for p in paths]:
				r.fetch()

		#TODO:output

	def update(self, recursive=False):
		#TODO: implement per repo update
		repos = self.repos.values()
		#if repos is None:
		#	repos = self.repos.values()
		#else:
		#	#TODO: turn list of strings into repos
		#	pass

		if self.dirty():
			raise RugError('Project has uncommitted changes - commit before updating')

		#TODO:update manifest?

		sub_repos = hierarchy.hierarchy(self.repos.keys())
		for r in repos:
			repo = r['repo']
			if repo:
				#Get Branch names, revs, etc.
				branches = self.get_branch_names(r)
				head_rev = repo.head()
				if not repo.valid_rev(branches['remote']):
					self.output.append('remote branch does not exist in %s: no update' % r['path'])
				else:
					remote_rev = repo.rev_class(repo, branches['remote'])
					#We don't touch the bookmark branch here - we refer to bookmark index branch if it exists,
					#or bookmark branch if not, and update the bookmark index branch if necessary.  Commit updates
					#bookmark branch and removes bookmark index
					if repo.valid_rev(branches['bookmark_index']):
						bookmark_rev = repo.rev_class(repo, branches['bookmark_index'])
					elif repo.valid_rev(branches['bookmark']):
						bookmark_rev = repo.rev_class(repo, branches['bookmark'])
					else:
						bookmark_rev = None

					#Check if there are no changes
					if head_rev.get_sha() == remote_rev.get_sha():
						self.output.append('%s is up to date with upstream repo: no update' % r['path'])
					elif head_rev.is_descendant(remote_rev):
						self.output.append('%s is ahead of upstream repo: no update' % r['path'])
					#Fast-Forward if we can
					elif head_rev.can_fastforward(remote_rev):
						self.output.append('%s is being fast-forward to upstream repo' % r['path'])
						repo.merge(remote_rev)
						repo.update_ref(branches['bookmark_index'], remote_rev)
					#otherwise rebase/merge local work
					elif bookmark_branch and head_rev.is_descendant(bookmark_branch):
						#TODO: currently dead code - we check for dirtyness at the top of the function
						if repo.dirty():
							#TODO: option to stash, rebase, then reapply?
							self.output.append('%s has local uncommitted changes and cannot be rebased. Skipping this repo.' % r['path'])
						else:
							#TODO: option to merge instead of rebase
							#TODO: handle merge/rebase conflicts
							#TODO: remember if we're in a conflict state
							self.output.append('%s is being rebased onto upstream repo' % r['name'])
							[ret,out,err] = repo.rebase(bookmark_branch, onto=branches['remote'])
							if ret:
								self.output.append(out)
							else:
								repo.update_ref(branches['bookmark_index'], branches['remote'])
					elif not bookmark_branch:
						self.output.append('%s has an unusual relationship with the remote branch, and no bookmark. Skipping this repo.' % r['path'])
					#Fail
					#TODO: currently dead code - we check for dirtyness at the top of the function
					elif head_rev.get_short_name() != r['revision']:
						self.output.append('%s has changed branches and cannot be safely updated. Skipping this repo.' % r['path'])
					else:
						#Weird stuff has happened - right branch, wrong relationship to bookmark
						self.output.append('You are out of your element.  The current branch in %s has been in altered in an unusal way and must be manually updated.' % r['path'])
			else:
				repo = self.create_repo(r, sub_repos[r['path']])
				self.output.append('Deleted repo %s check out' % r['path'])

			if recursive:
				repo.update(recursive)

	def add(self, path, name=None, remote=None, rev=None, vcs=None, use_sha=None):
		#TODO:handle lists of dirs
		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		lookup_default = {}
		lookup_default.update(RUG_DEFAULT_DEFAULT)
		lookup_default.update(default)

		update_rug_branch = False

		#TODO: possibly push some of this into the wrapper

		r = self.wrappers.get(path, None)
		if r is None:
			# Validate inputs
			if name is None:
				raise RugError('new repos must specify a name')
			if remote is None:
				raise RugError('new repos must specify a remote')
			if self.bare:
				if rev is None:
					raise RugError('new repos in bare projects must specify a rev')
				if vcs is None:
					raise RugError('new repos in bare projects must specify a vcs')

		if self.bare:
			#Can't really test/validate anything here since there's no repo
			#Hope the user knows what they're doing

			#Add the repo
			repos[path] = {'path': path}

			revision = rev
		else:
			if r is None:
				#New repository
				#Find vcs if not specified, and create repo object
				abs_path = os.path.join(self.dir, path)
				if vcs is None:
					repo = None
					#TODO: rug needs to take priority here, as rug repos with sub-repos at '.'
					#will look like the sub-repo vcs as well as a rug repo
					#(but not if the path of the sub-repo is '.')
					for (try_vcs, R) in self.vcs_class.items():
						if R.valid_repo(abs_path):
							repo = R(abs_path, output_buffer=self.output.spawn(path + ': '))
							vcs = try_vcs
							break
					if repo is None:
						raise RugError('unrecognized repo %s' % path)
				else:
					repo = self.vcs_class[vcs](abs_path, output_buffer=self.output.spawn(path + ': '))

				#Add the repo
				repos[path] = {'path': path}

				#TODO: we don't know if the remote even exists yet, so can't set up all branches
				#logic elsewhere should be able to handle this possibility (remote & bookmark branches don't exist)
				update_rug_branch = True

				#TODO: should this be required?  If not, what should the default be?
				if use_sha is None:
					use_sha = False
			else:
				#Modify existing repo
				repo = r.repo

				#TODO: rethink this condition
				if remote is not None:
					update_rug_branch = True

				#If use_sha is not specified, look at existing manifest revision
				if use_sha is None:
					use_sha = r.valid_sha(r.revision)

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
			pval = locals()[p]
			if (pval is not None) and (pval != lookup_default.get(p)):
				repos[path][p] = pval

		#Write the manifest and reload repos
		manifest.write(self.manifest_filename, remotes, repos, default)
		self.import_manifest()

		if not self.bare:
			r = self.repos[path]
			repo = r['repo']
			branches = self.get_branch_names(r)

			#Update rug_index
			repo.update_ref(branches['rug_index'], rev)

			#If this is a new repo, set the rug branch
			if update_rug_branch:
				repo.update_ref(branches['rug'], rev)

		self.output.append("%s added to manifest" % path)

	def bind(self, message=None, recursive=True):
		for r in self.repos.values():
			r.bind(message=message, recursive=recursive)
			self.add(r.path, use_sha=True)
		self.commit(message=message)

		#adding sub-repos with use_sha=True doesn't actually change the HEAD.  checkout will do that
		#TODO: this may not be the right place for this.  Should it happen in add or commit?
		self.checkout()

	def remove(self, path):
		'''Remove a repo from the manifest'''

		(remotes, repos, default) = manifest.read(self.manifest_filename, apply_default=False)
		lookup_default = {}
		lookup_default.update(RUG_DEFAULT_DEFAULT)
		lookup_default.update(default)

		if path not in repos:
			raise RugError('unrecognized repo %s' % path)

		del(repos[path])

		manifest.write(self.manifest_filename, remotes, repos, default)
		self.import_manifest()

		self.output.append("%s removed from manifest" % path)

	def commit(self, message=None, all=False, recursive=False):
		if not self.bare:
			for r in self.repos.values():
				if all:
					#commit if needed
					#Note: 'recursive' without 'all' makes no sense
					if recursive and r.dirty():
						if message is None:
							raise RugError('commit message required')
						r.commit(message, all=True, recursive=True)
					#add if needed
					status = r.status(porcelain=True, recursive=False)
					if ('B' in status) or ('R' in status):
						self.add(r.path)
						r = self.repos[r.path]
				branches = r.get_branch_names()
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

		self.output.append("committed revset %s to %s" % (self.revset().get_short_name(), self.dir))

	def push(self, source=None, test=False, output_buffer=None):
		if source is None:
			source = 'origin'
		if not source in self.source_list():
			raise RugError('unrecognized source %s' % source)

		#Committed revset info
		manifest_blob_id = self.manifest_repo.get_blob_id('manifest.xml')
		commit_repos = manifest.read_from_string(
				self.manifest_repo.show(manifest_blob_id),
				default_default=RUG_DEFAULT_DEFAULT
			)[1]

		#TODO: use manifest.read with apply_default=False
		if output_buffer is None:
			if test:
				output_buffer = output.NullOutputBuffer()
			else:
				output_buffer = self.output

		#Verify that we can push to all unpushed remotes
		success = True

		if not self.bare:
			for r in commit_repos.values():
				repo = wrapper.Wrapper(self, output_buffer=output_buffer, **r)
				if repo.should_push():
					if not repo.push(test=test):
						success = False

		#Verify that we can push to manifest repo
		#TODO: We don't always need to push manifest repo
		manifest_revision = self.revset()
		if manifest_revision.is_sha():
			manifest_refspec = '%s:refs/heads/%s' % (manifest_revision.get_sha(), RUG_SHA_RIDER)
			manifest_force = True
		else:
			manifest_refspec = manifest_revision.get_short_name()
			manifest_force = False

		if not self.manifest_repo.push(source, manifest_refspec, force=manifest_force, test=test):
			output.append('manifest branch %s cannot be pushed to %s' % (manifest_revision.get_short_name(), source))
			success = False

		if test:
			return success
		elif not success:
			#this shouldn't happen - an error should be raised at the failure point
			raise RugError('error on push')

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
