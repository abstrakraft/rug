import os.path
import subprocess
import string
import output

GIT = 'git'
GIT_DIR = '.git'

class GitError(StandardError):
	pass

class InvalidRepoError(GitError):
	pass

class UnknownRevisionError(GitError):
	pass

def shell_cmd(cmd, args, cwd=None, raise_errors=True):
	'''shell_cmd(cmd, args, cwd=None, raise_errors=True) -> runs a shell command
	raise_errors=True: returns stdout
	raise_errors=False: returns (returncode, stdout, stderr)'''

	if cwd:
		proc = subprocess.Popen([cmd]+args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	else:
		proc = subprocess.Popen([cmd]+args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

	(out, err) = proc.communicate()
	ret = proc.returncode
	if raise_errors:
		if ret != 0:
			raise GitError('%s %s: %s' % (cmd, ' '.join(args), err))
		else:
			return out.rstrip()
	else:
		return (ret, out, err)

class Rev(object):
	def __init__(self, repo_finder, name, unchecked=False):
		repo = self.find_repo(repo_finder)
		if (not unchecked) and (not repo.valid_rev(name)):
			raise UnknownRevisionError('invalid rev %s' % name)

		self.repo_finder = repo_finder
		self.repo = repo
		self.name = name

	@staticmethod
	def find_repo(repo_finder):
		return repo_finder

	@classmethod
	def cast(cls, repo_finder, rev):
		if isinstance(rev, Rev):
			unchecked = (rev.repo.dir == cls.find_repo(repo_finder).dir)
			return cls(repo_finder, rev.name, unchecked=unchecked)
		else:
			return cls(repo_finder, rev)

	@classmethod
	def create(cls, repo_finder, dst, src=None):
		repo = cls.find_repo(repo_finder)

		if src is None:
			src = cls(repo, 'HEAD')

		repo.branch_create(dst, src)

		return cls(repo_finder, dst)

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

	def __cmp__(self, other):
		return self.get_short_name() == self.get_short_name()

	def is_descendant(self, rev):
		rev = self.cast(self.repo_finder, rev)
		return rev.get_sha() in self.repo.git_func(['rev-list', self.get_short_name()]).split()

	def merge_base(self, rev):
		cls = type(self)
		rev = self.cast(self.repo_finder, rev)
		return cls.cast(self.repo_finder, \
			self.repo.git_func(['merge-base', self.get_short_name(), rev.get_short_name()]))

	def can_fastforward(self, rev):
		return self.get_sha() == self.merge_base(rev).get_sha()

class Repo(object):
	rev_class = Rev

	def __init__(self, repo_dir, output_buffer=None):
		if output_buffer is None:
			output_buffer = output.NullOutputBuffer()
		self.output = output_buffer
		abs_dir = os.path.abspath(repo_dir)
		if not self.valid_repo(abs_dir):
			raise InvalidRepoError('not a valid git repository')
		self.dir = abs_dir
		self.bare = (self.git_func(['config', 'core.bare']).lower() == 'true')
		if self.bare:
			self.git_dir = self.dir
		else:
			self.git_dir = os.path.join(self.dir, GIT_DIR)

	@classmethod
	def valid_repo(cls, repo_dir):
		return os.path.exists(os.path.join(repo_dir, GIT_DIR)) or \
			(os.path.exists(repo_dir) and (shell_cmd(GIT, ['config', 'core.bare'], cwd=repo_dir, raise_errors=False)[1].lower() == 'true\n'))

	@classmethod
	def init(cls, repo_dir=None, bare=None, output_buffer=None):
		if output_buffer is None:
			output_buffer = output.NullOutputBuffer()

		args = ['init']
		if bare: args.append('--bare')
		if repo_dir: args.append(repo_dir)

		shell_cmd(GIT, args)
		if repo_dir is None:
			return cls('.', output_buffer=output_buffer)
		else:
			return cls(repo_dir, output_buffer=output_buffer)

	@classmethod
	def clone(cls, url, repo_dir=None, remote=None, rev=None, local_branch=None, config=None, output_buffer=None):
		if output_buffer is None:
			output_buffer = output.NullOutputBuffer()

		if remote is None:
			remote = 'origin'

		#A manual clone is necessary to avoid git's check for an empty directory.
		#Really need to find another method - manual clone is a maintenance PITA
		do_standard = False
		if do_standard:
			args = ['clone', url]
			if repo_dir:
				args.append(repo_dir)
		
			shell_cmd(GIT, args)
			return cls(repo_dir, output_buffer=output_buffer)
		else:
			if repo_dir:
				if not os.path.exists(repo_dir):
					os.makedirs(repo_dir)
			else:
				repo_dir = os.getcwd()

			repo = cls.init(repo_dir, output_buffer=output_buffer)
			if config is not None:
				for (name, value) in config.items():
					repo.config(name, value)
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

	def git_cmd(self, args, raise_errors=True, return_output=False):
		'''git_cmd(args, raise_errors=True, return_output=False) -> runs a shell command
		return_output=False: returns None, appends stdout to output buffer
		return_output=True, raise_errors=True: returns stdout
		return_output=True, raise_errors=False: returns (returncode, stdout, stderr)'''
		#if hasattr(self, 'git_dir'):
		#	return shell_cmd(GIT, args + ['--git-dir=%s' % self.git_dir])
		#else:
		ret = shell_cmd(GIT, args, cwd = self.dir, raise_errors=raise_errors)

		if raise_errors:
			stdout = ret
		else:
			(returncode, stdout, stderr) = ret

		if return_output:
			return ret
		else:
			self.output.append(stdout)

	def git_func(self, args, raise_errors=True):
		'''git_func(args, raise_errors=True) -> shorthand for git_cmd(args, raise_errors, return_output=True)'''
		return self.git_cmd(args, raise_errors, return_output=True)

	def head(self):
		return Rev(self, 'HEAD')

	def dirty(self, ignore_submodules=True):
		args = ['diff', 'HEAD']
		if ignore_submodules:
			args.append('--ignore-submodules')

		#TODO: doesn't account for untracked files (should it?)
		return not (len(self.git_func(args)) == 0)

	def remote_list(self):
		return self.git_func(['remote', 'show']).split()

	def remote_add(self, remote, url):
		self.git_cmd(['remote','add', remote, url])

	def remote_set_head(self, remote, suppress_output=True):
		if suppress_output:
			f = self.git_func
		else:
			f = self.git_cmd
		f(['remote', 'set-head', remote, '-a'])

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

	def push(self, remote=None, refspec=None, force=False):
		args = ['push']
		if force: args.append('-f')
		if remote: args.append(remote)
		if refspec:
			#refspec may be %s:%s rather than just a branch name, so can't cast
			if isinstance(refspec, Rev):
				args.append(refspec.get_short_name())
			else:
				args.append(refspec)

		self.git_cmd(args)

	def test_push(self, remote=None, refspec=None, force=False):
		args = ['push', '-n']
		if force: args.append('-f')
		if remote: args.append(remote)
		if refspec:
			#refspec may be %s:%s rather than just a branch name, so can't cast
			if isinstance(refspec, Rev):
				args.append(refspec.get_short_name())
			else:
				args.append(refspec)

		(ret, out, err) = self.git_func(args, raise_errors=False)
		return not ret

	#TODO: doesn't work
	#def branch_list(self, all=False):
	#	args = ['branch']
	#	if all:
	#		args.append('-a')

	#	return self.git_cmd(args).split()

	def ref_list(self):
		args = ['show-ref']
		return map(Rev, [r.split()[1][5:] for r in self.git_func(args).split('\n')])

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

	def update(self, recursive=False):
		#Stub for recursive updates
		pass

	def stash(self):
		self.git_cmd(['stash'])

	def stash_pop(self):
		self.git_cmd(['stash', 'pop'])

	def update_ref(self, ref, newval):
		#ref may not exist, so can't Rev.cast
		if isinstance(ref, Rev):
			ref = ref.get_long_name()
		if isinstance(newval, Rev):
			newval = newval.get_long_name()
		self.git_cmd(['update-ref', ref, newval])

	def delete_ref(self, ref):
		self.git_cmd(['update-ref', '-d', Rev.cast(self, ref).get_long_name()])

	#Branch combination operations
	#these commands do not currently raise errors
	#TODO:differentiate between errors and conflicts, act accordingly

	def merge(self, merge_head):
		return self.git_func(['merge', Rev.cast(self, merge_head).get_short_name()], raise_errors=False)

	def rebase(self, base, onto=None):
		args = ['rebase']
		if onto:
			args.extend(['--onto', onto])
		args.append(Rev.cast(self, base).get_short_name())

		return self.git_func(args, raise_errors=False)

	def config(self, name, value=None):
		if value is None:
			return self.git_func(['config', name])
		else:
			self.git_cmd(['config', name, value])

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

		return self.git_func(args)

	def diff(self):
		return self.git_func(['diff'])

	def rev_parse(self, rev, full_name=False, abbrev_ref=False):
		args = ['rev-parse']
		if full_name:
			args.append('--symbolic-full-name')
		if abbrev_ref:
			args.append('--abbrev-ref')
		args.append(rev)

		try:
			return self.git_func(args)
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

	def symbolic_ref(self, ref):
		return self.git_func(['symbolic-ref', ref])
