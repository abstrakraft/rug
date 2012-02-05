import os.path
import subprocess
import string

GIT='git'
GIT_DIR='.git'

class GitError(StandardError):
	pass

class InvalidRepoError(GitError):
	pass

class UnknownRevisionError(GitError):
	pass

def shell_cmd(cmd, args, cwd=None, raise_errors=True, print_output=False):
	'''shell_cmd(cmd, args, cwd=None, raise_errors=True, print_output=False) -> runs a shell command
	default: returns None
	raise_errors=True, print_output=False: returns standard output
	raise_errors=False: returns (ret, stdout, stderr)'''
	if print_output:
		stdout = None
	else:
		stdout = subprocess.PIPE

	if cwd:
		proc = subprocess.Popen([cmd]+args, cwd=cwd, stdout=stdout, stderr=subprocess.PIPE)
	else:
		proc = subprocess.Popen([cmd]+args, stdout=stdout, stderr=subprocess.PIPE)

	(out, err) = proc.communicate()
	ret = proc.returncode
	if raise_errors:
		if ret != 0:
			raise GitError('%s %s: %s' % (cmd, ' '.join(args), err))
		elif print_output:
			return
		else:
			return out.rstrip()
	else:
		return (ret, out, err)

class Rev(object):
	def __init__(self, repo, name):
		if not repo.valid_rev(name):
			raise UnknownRevisionError('invalid rev %s' % name)

		self.repo = repo
		self.name = name

	@classmethod
	def cast(cls, repo, rev):
		if isinstance(rev, cls):
			return rev
		else:
			return cls(repo, rev)

	@classmethod
	def create(cls, repo, dst, src=None):
		if src is None:
			src = cls(repo, 'HEAD')

		repo.branch_create(dst, src)

		return cls(repo, dst)

	def is_sha(self):
		if '_is_sha' not in self.__dict__:
			self._is_sha = self.repo.valid_sha(self.name)
		return self._is_sha

	def get_sha(self):
		return self.repo.rev_parse(self.name)

	def get_short_name(self):
		if self.is_sha():
			return self.name
		else:
			return self.repo.rev_parse(self.name, abbrev_ref=True)

	def get_long_name(self):
		if self.is_sha():
			return self.get_sha()
		else:
			return self.repo.rev_parse(self.name, full_name=True)

class Repo(object):
	def __init__(self, repo_dir):
		abs_dir = os.path.abspath(repo_dir)
		if not self.valid_repo(abs_dir):
			raise InvalidRepoError('not a valid git repository')
		self.dir = abs_dir
		self.bare = (self.git_cmd(['config', 'core.bare']).lower() == 'true')
		if self.bare:
			self.git_dir = self.dir
		else:
			self.git_dir = os.path.join(self.dir, GIT_DIR)

	@classmethod
	def valid_repo(cls, repo_dir):
		return os.path.exists(os.path.join(repo_dir, GIT_DIR)) or \
			(os.path.exists(repo_dir) and (shell_cmd(GIT, ['config', 'core.bare'], cwd=repo_dir, raise_errors=False)[1].lower() == 'true\n'))

	@classmethod
	def init(cls, repo_dir=None, bare=None):
		args = ['init']
		if bare: args.append('--bare')
		if repo_dir: args.append(repo_dir)

		shell_cmd(GIT, args)
		if repo_dir is None:
			return cls('.')
		else:
			return cls(repo_dir)

	@classmethod
	def clone(cls, url, repo_dir=None, remote=None, rev=None, local_branch=None):
		if remote is None:
			remote = 'origin'

		#A manual clone is necessary to avoid git's check for an empty directory.
		#Really need to find another method - manual clone is a maintenance PITA
		#method = 'standard'
		method = 'manual'
		if method == 'standard':
			args = ['clone', url]
			if repo_dir:
				args.append(repo_dir)
		
			shell_cmd(GIT, args)
			return cls(repo_dir)
		elif method == 'manual':
			if repo_dir:
				if not os.path.exists(repo_dir):
					os.makedirs(repo_dir)
			else:
				repo_dir = os.getcwd()

			repo = cls.init(repo_dir)
			repo.remote_add(remote, url)
			repo.fetch(remote)
			#TODO: weirdness: Git can't actually tell what the HEAD of the remote is directly,
			#just what it's SHA is.  Which means that if multiple remote branches are at the HEAD sha,
			#git can't tell which is the actual HEAD.  'git remote set-head -a' errors in this case.
			#Amazingly, 'git clone' just guesses, and may guess wrong.  This behavior is seriously broken.
			#see guess_remote_host in git/remote.c
			repo.remote_set_head(remote)

			if rev and repo.valid_sha(rev):
				#rev is a Commit ID
				repo.checkout(rev)
			else:
				if rev:
					remote_branch = Rev(repo, '%s/%s' % (remote, rev))
					if not local_branch:
						local_branch = rev
				else:
					remote_branch = Rev(repo, 'refs/remotes/%s/HEAD' % remote)
					if not local_branch:
						#remove refs/remotes/<origin>/ for the local version
						local_branch = '/'.join(remote_branch.get_long_name().split('/')[3:])
				#Strange things can happen here if local_branch is 'master', since git considers
				#the repo to be on branch master, although it doesn't technically exist yet.
				#'checkout -b' doesn't quite to know what to make of this situation, so we branch
				#explicitly.  Also, checkout will try to merge local changes into the checkout
				#(which will delete everything), so we force a clean checkout
				local_branch = Rev.create(repo, local_branch, remote_branch)
				repo.checkout(local_branch, force=True)

			return repo

	def git_cmd(self, args, raise_errors=True, print_output=False):
		#if hasattr(self, 'git_dir'):
		#	return shell_cmd(GIT, args + ['--git-dir=%s' % self.git_dir])
		#else:
		return shell_cmd(GIT, args, cwd = self.dir, raise_errors=raise_errors, print_output=print_output)

	def head(self):
		return Rev(self, 'HEAD')

	def dirty(self, ignore_submodules=True):
		args = ['diff', 'HEAD']
		if ignore_submodules:
			args.append('--ignore-submodules')

		#TODO: doesn't account for untracked files (should it?)
		return not (len(self.git_cmd(args)) == 0)

	def remote_list(self):
		return self.git_cmd(['remote', 'show']).split()

	def remote_add(self, remote, url):
		self.git_cmd(['remote','add', remote, url])

	def remote_set_head(self, remote):
		self.git_cmd(['remote', 'set-head', remote, '-a'])

	def remote_set_url(self, remote, url):
		self.git_cmd(['remote','set-url', remote, url])

	def fetch(self, remote=None):
		args = ['fetch', '-v']
		if remote: args.append(remote)

		self.git_cmd(args)

	def add(self, *files):
		args = ['add']
		args.extend(files)
		self.git_cmd(args)

	def commit(self, message, all=False):
		args = ['commit']
		if all: args.append('-a')
		args.extend(['-m', message])

		self.git_cmd(args)

	def push(self, remote=None, branch=None, force=False):
		args = ['push']
		if force: args.append('-f')
		if remote: args.append(remote)
		if branch: args.append(Rev.cast(self, branch).get_short_name())

		self.git_cmd(args)

	def test_push(self, remote=None, branch=None, force=False):
		args = ['push', '-n']
		if force: args.append('-f')
		if remote: args.append(remote)
		if branch: args.append(Rev.cast(self, branch).get_short_name())

		(ret, out, err) = self.git_cmd(args, raise_errors=False)
		return not ret

	#TODO: doesn't work
	#def branch_list(self, all=False):
	#	args = ['branch']
	#	if all:
	#		args.append('-a')

	#	return self.git_cmd(args).split()

	def ref_list(self):
		args = ['show-ref']
		return map(Rev, [r.split()[1][5:] for r in self.git_cmd(args).split('\n')])

	def branch_create(self, dst, src=None, force=False):
		args = ['branch']
		if force:
			args.append('-f')
		args.append(dst)
		if src:
			args.append(Rev.cast(self, src).get_short_name())

		self.git_cmd(args)

	def branch_delete(self, dst, force=False):
		args = ['branch']
		if force:
			args.append('-D')
		else:
			args.append('-d')
		args.append(Rev.cast(self, dst).get_short_name())

		self.git_cmd(args)

	def checkout(self, branch, force=False):
		args = ['checkout']
		if force:
			args.append('-f')
		args.append(Rev.cast(self, branch).get_short_name())

		self.git_cmd(args)

	SOFT = 0
	MIXED = 1
	HARD = 2
	def reset(self, branch, mode=None):
		args = ['reset']
		if mode is not None:
			if mode == 0:
				args.append('--soft')
			elif mode == 1:
				args.append('--mixed')
			elif mode == 2:
				args.append('--hard')
			else:
				#TODO: error
				pass
		args.append(Rev.cast(self, branch).get_short_name())
		self.git_cmd(args)

	def update_ref(self, ref, newval):
		#ref may not exist, so can't Rev.cast
		if isinstance(ref, Rev):
			ref = ref.get_long_name()
		self.git_cmd(['update-ref', ref, newval])

	#Branch combination operations
	#these commands do not currently raise errors
	#TODO:differentiate between errors and conflicts, act accordingly

	def merge(self, merge_head):
		return self.git_cmd(['merge', merge_head], raise_errors=False, print_output=False)

	def rebase(self, base, onto=None):
		args = ['rebase']
		if onto:
			args.extend(['--onto', onto])
		args.append(Rev.cast(self, base).get_short_name())

		return self.git_cmd(args, raise_errors=False, print_output=False)

	def add_ignore(self, pattern):
		f = open(os.path.join(self.dir, GIT_DIR, 'info', 'exclude'), 'a')
		f.write(pattern + '\n')
		f.close()

	#Query functions
	def status(self, porcelain=True):
		#TODO: parse status output, or leave as text?
		args = ['status']
		if porcelain:
			args.append('--porcelain')

		return self.git_cmd(args, raise_errors=True, print_output=False)

	def diff(self):
		return self.git_cmd(['diff'])

	def rev_parse(self, rev, full_name=False, abbrev_ref=False):
		args = ['rev-parse']
		if full_name:
			args.append('--symbolic-full-name')
		if abbrev_ref:
			args.append('--abbrev-ref')
		args.append(rev)

		try:
			return self.git_cmd(args)
		except GitError as e:
			if e.args[0].find('unknown revision') > -1:
				raise UnknownRevisionError('Unknown revision %s' % rev)
			else:
				raise e

	def valid_rev(self, rev, include_sha=True):
		if include_sha:
			try:
				self.rev_parse(rev)
			except UnknownRevisionError:
				return False

			return True
		else:
			if self.valid_sha(rev):
				return False
			else:
				return self.valid_rev(rev, include_sha=True)

	def valid_sha(self, rev):
		#Note: this will fail for revs that are prefixes of their own SHAs
		#However, if you name your branches that way, you deserve what you get
		try:
			rp = self.rev_parse(rev)
		except UnknownRevisionError:
			return False

		return rp[:len(rev)] == rev

	def merge_base(self, rev1, rev2):
		#TODO: return Rev
		return self, self.git_cmd(['merge-base', Rev.cast(self, rev1).get_short_name(), Rev.cast(self, rev2).get_short_name()])

	def symbolic_ref(self, ref):
		return self.git_cmd(['symbolic-ref', ref])

	def can_fastforward(self, merge_head, orig_head = 'HEAD'):
		#TODO: handle Rev from merge_base
		return self.rev_parse(orig_head) == self.merge_base(orig_head, merge_head)

	def is_descendant(self, ancestor, branch=None):
		if branch is None:
			branch = 'HEAD'
		return Rev.cast(self, ancestor).get_sha() in self.git_cmd(['rev-list', Rev.cast(self, branch).get_short_name()]).split()
