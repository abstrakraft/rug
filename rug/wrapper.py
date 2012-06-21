import os
import hierarchy

from rug_common import *

class Wrapper(object):
	vcs_class = {}

	def __init__(self, parent, vcs, path, remote, revision, name, output_buffer):
		self.parent = parent
		self.vcs = vcs
		self.path = path
		self.remote = remote
		self.revision = revision
		self.name = name
		self.output = output_buffer.spawn(path + ': ')

		if self.parent.bare:
			self.repo = None
		else:
			abs_path = os.path.abspath(os.path.join(self.parent.dir, path))
			R = self.vcs_class[self.vcs]
			if R.valid_repo(abs_path):
				self.repo = R(abs_path, self.output)
			else:
				self.repos = None

	@classmethod
	def register_vcs(cls, vcs, vcs_class):
		cls.vcs_class[vcs] = vcs_class

	def get_branch_names(self):
		revision = self.revision
		if revision == 'HEAD':
			start = len('refs/remotes/%s/' % self.remote)
			revision = self.repo.symbolic_ref('refs/remotes/%s/HEAD' % self.remote)[start:]
		ret = {}
		if self.repo.valid_sha(revision):
			#TODO: rethink how this works for sha repos
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = revision
			ret['rug'] = 'refs/rug/heads/%s/%s/sha/rug_index' % (self.parent.revset().get_short_name(), self.remote)
			ret['rug_index'] = 'refs/rug/rug_index'
			ret['bookmark'] = 'refs/rug/bookmarks/%s/%s/sha/bookmark' % (self.parent.revset().get_short_name(), self.remote)
			ret['bookmark_index'] = 'refs/rug/bookmark_index'
			ret['remote'] = revision
		else:
			ret['live_porcelain'] = revision
			ret['live_plumbing'] = 'refs/heads/%s' % revision
			ret['rug'] = 'refs/rug/heads/%s/%s/%s' % (self.parent.revset().get_short_name(), self.remote, revision)
			ret['rug_index'] = 'refs/rug/rug_index'
			ret['bookmark'] = 'refs/rug/bookmarks/%s/%s/%s' % (self.parent.revset().get_short_name(), self.remote, revision)
			ret['bookmark_index'] = 'refs/rug/bookmark_index'
			ret['remote'] = '%s/%s' % (r['remote'], revision)

		return ret

	def status(self, commit_r, porcelain=True, recursive=True):
		#"Index" (manifest working tree) info is in self properties
		#Working tree info comes from self.repo

		#Status1: commit..index diff
		if not commit_r:
			status1 = 'A'
		elif commit_r['revision'] != self.revision:
			status1 = 'R'
		else:
			status1 = ' '

		#Status2: index..working_tree diff
		if not self.repo:
			status2 = 'D'
		else:
			branches = self.get_branch_names()
			head = self.repo.head()
			if self.repo.valid_sha(self.revision):
				#the revision in the manifest could be an abbreviation
				if head.get_sha().startswith(self.revision):
					status2 = ' '
				else:
					#Revision changed names: Revision
					status2 = 'R'
			else:
				if (head.get_short_name() != index.revision):
					#Revision changed names: Revision
					status2 = 'R'
				else:
					if self.repo.valid_rev(branches['rug_index']):
						index_branch = branches['rug_index']
					else:
						index_branch = branches['rug']
					index_rev = self.repo.rev_class(self.repo, index_branch)
					if head.get_sha() == index_rev.get_sha():
						status2 = ' '
					else:
						#Branch definition changed: Branch
						status2 = 'B'

		rug_status = status1 + status2

		if recursive:
			if self.repo:
				repo_status = self.repo.status(porcelain=porcelain)
			else:
				repo_status = None
			return (rug_status, repo_status)
		else:
			return rug_status

	def dirty(self):
		#currently, "dirty" is defined as "would commit -a do anything"
		return (self.status(None, porcelain=True, recursive=False)[1] != ' ') or (self.repo and self.repo.dirty())

	def create_repo(self):
		if self.parent.bare:
			raise RugError('Invalid operation for bare project')

		abs_path = os.path.abspath(os.path.join(self.parent.dir, r.path))
		url = self.parent.remotes[r.remote]['fetch'] + '/' + r.name
		R = self.vcs_class[r.vcs]

		config = self.parent.get_rug_config()
		repo = R.clone(url, repo_dir=abs_path, remote=self.remote, rev=self.revision, config=config, output_buffer=self.output.spawn(self.path + ': '))
		if self.path == '.':
			repo.add_ignore(RUG_DIR)
			cmp_path = ''
		else:
			cmp_path = self.path
		relevant_paths = [p for p in self.parent.repos if len(p) > len(cmp_path) and p.startswith(cmp_path)]
		sub_repos = hierarchy.hierarchy(relevant_paths, fullpath=False)[self.path]
		for sr in sub_repos:
			repo.add_ignore(sr)
		self.repo = repo
		branches = self.get_branch_names()
		for b in ['live_plumbing', 'rug', 'bookmark']:
			self.repo.update_ref(branches[b], branches['remote'])

		self.repo.checkout(branches['live_porcelain'])

	def checkout(self):
		#if the repo doesn't exist, clone it
		if not self.repo:
			self.create_repo()
		else:
			self.verify_remote(r)

			#Fetch from remote
			#TODO:decide if we should always do this here.  Sometimes have to, since we may not have
			#seen this remote before.  If we have to do it sometimes, maybe should do it always
			self.repo.fetch(self.remote)

			branches = self.get_branch_names()

			#create rug and bookmark branches if they don't exist
			#branches are fully qualified ('refs/...') branch names, so use update_ref
			#instead of create_branch
			for b in ['rug', 'bookmark']:
				if not self.repo.valid_rev(branches[b]):
					self.repo.update_ref(branches[b], branches['remote'])

			for b in ['rug_index', 'bookmark_index']:
				if self.repo.valid_rev(branches[b]):
					self.repo.delete_ref(branches[b])

			#create and checkout the live branch
			self.repo.update_ref(branches['live_plumbing'], branches['rug'])
			self.repo.checkout(branches['live_porcelain'])

	def verify_remote(self, remotes = None):
		if remotes is None:
			remotes = self.parent, remotes
		url = remotes[self.remote]]['fetch'] + '/' + self.name

		if self.remote not in self.repo.remote_list():
			self.repo.remote_add(self.remote, url)
		else:
			if r.vcs == 'rug':
				candidate_urls = map(lambda c: c % url, RUG_CANDIDATE_TEMPLATES)
				if self.repo.config('remote.%s.url' % self.remote) not in candidate_urls:
					clone_url = None
					for cu in candidate_urls:
						if git.Repo.valid_repo(cu, config=repo_config):
							clone_url = cu
							break
					if clone_url:
						self.repo.remote_set_url(self.remote, clone_url)
					else:
						raise RugError('%s does not seem to be a rug project' % url)
			else:
				self.repo.remote_set_url(self.remote, url)

	def fetch(self, remote=None):
		if remote is None:
			remote = self.remote
		self.repo.fetch(remote)
		self.repo.remote_set_head(remote)

	def bind(self, message, recursive=True):
		if recursive and r['vcs'] == 'rug':
			self.repo.bind(message=message, recursive=recursive)

	def commit(self, message, all=False, recursive=False):
		if r.vcs == 'rug':
			self.repo.commit(message=message, all=all, recursive=recursive)
		else:
			self.repo.commit(message=message, all=all)

	def should_push(self)
		branches = self.get_branch_names()
		if not self.repo.valid_rev(branches['remote']):
			return True
		else:
			rug_rev = self.repo.rev_class(self.repo, branches['rug'])
			remote_rev = self.repo.rev_class(self.repo, branches['remote'])
			return rug_rev.get_sha() != remote_rev.get_sha()

	def push(self, test=False):
		#TODO: verify correctness & consistency of path functions/formats throughout rug
		branches = self.get_branch_names()
		if self.repo.valid_sha(self.revision):
			#TODO: PROBLEM: branches pushed as sha_riders may not have heads associated with them,
			#which means that clones won't pull them down
			refspec = '%s:refs/heads/%s' % (self.revision, RUG_SHA_RIDER)
			force = True
		else:
			refspec = '%s:refs/heads/%s' % (branches['rug'], self.revision)
			force = False

		if not self.repo.push(self.remote, refspec, force=force, test=test):
			self.output.append('%s: %s cannot be pushed to %s' % (self.name, self.revision, self.remote))
			return False
		else:
			if not test:
				self.repo.update_ref(branches['bookmark'], branches['rug'])
				self.output.append('%s: pushed %s to %s' % (self.name, self.revision, self.remote))

			return True
