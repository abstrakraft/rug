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

class Repo(object):
	def __init__(self, dir):
		d = os.path.abspath(dir)
		if not self.valid_repo(d):
			raise InvalidRepoError('not a valid git repository')
		self.dir = d
		self.bare = (self.git_cmd(['config', 'core.bare']).lower() == 'true')
		if self.bare:
			self.git_dir = self.dir
		else:
			self.git_dir = os.path.join(self.dir, GIT_DIR)

	@classmethod
	def valid_repo(cls, dir):
		#return not shell_cmd(GIT, ['remote', 'show'], cwd)[0]
		return os.path.exists(os.path.join(dir, GIT_DIR)) or \
			(os.path.exists(dir) and (shell_cmd(GIT, ['config', 'core.bare'], cwd=dir, raise_errors=False)[1].lower() == 'true'))

	@classmethod
	def init(cls, dir=None, bare=None):
		args = ['init']
		if bare: args.append('-b')
		if dir: args.append(dir)

		shell_cmd(GIT, args)
		if dir is None:
			return cls('.')
		else:
			return cls(dir)

	@classmethod
	def clone(cls, url, dir=None, remote=None, rev=None, local_branch=None):
		if remote is None:
			remote = 'origin'

		#A manual clone is necessary to avoid git's check for an empty directory.
		#Really need to find another method - manual clone is a maintenance PITA
		#method = 'standard'
		method = 'manual'
		if method == 'standard':
			args = ['clone', url]
			if dir:
				args.append(dir)
		
			shell_cmd(GIT, args)
			return cls(dir)
		elif method == 'manual':
			if dir:
				if not os.path.exists(dir):
					os.makedirs(dir)
			else:
				dir = os.getcwd()

			shell_cmd(GIT, ['init'], cwd=dir)
			repo = cls(dir)
			repo.remote_add(remote, url)
			repo.fetch(remote)
			#TODO: weirdness: Git can't actually tell what the HEAD of the remote is directly,
			#just what it's SHA is.  Which means that if multiple remote branches are at the HEAD sha,
			#git can't tell which is the actual HEAD.  'git remote set-head -a' errors in this case.
			#Amazingly, 'git clone' just guesses, and may guess wrong.  This behavior is seriously broken.
			#see guess_remote_host in git/remote.c
			repo.remote_set_head(remote)

			if rev and repo.valid_ref(rev):
				#rev is a Commit ID
				repo.checkout(rev)
			else:
				if rev:
					remote_branch = '%s/%s' % (remote, rev)
					if not local_branch:
						local_branch = rev
				else:
					remote_branch = repo.symbolic_ref('refs/remotes/%s/HEAD' % remote)
					if not local_branch:
						#remove refs/remotes/<origin>/ for the local version
						local_branch = '/'.join(remote_branch.split('/')[3:])
				#Strange things can happen here if local_branch is 'master', since git considers
				#the repo to be on branch master, although it doesn't technically exist yet.
				#'checkout -b' doesn't quite to know what to make of this situation, so we branch
				#explicitly.  Also, checkout will try to merge local changes into the checkout
				#(which will delete everything), so we force a clean checkout
				repo.branch_create(local_branch, remote_branch)
				repo.checkout(local_branch, force=True)

			return repo

	def git_cmd(self, args, raise_errors=True, print_output=False):
		#if hasattr(self, 'git_dir'):
		#	return shell_cmd(GIT, args + ['--git-dir=%s' % self.git_dir])
		#else:
		return shell_cmd(GIT, args, cwd = self.dir, raise_errors=raise_errors, print_output=print_output)

	def head(self, full=False):
		ref = open(os.path.join(self.git_dir, 'HEAD')).read()

		if ref.startswith('ref: '):
			ref = ref[5:-1]
			if not full:
				parts = ref.split('/')
				if (len(parts) > 2) and (parts[0] == 'refs') and ((parts[1] == 'heads') or (parts[1] == 'tags')):
					ref = '/'.join(parts[2:])
		else:
			ref = ref[:-1]

		return ref

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
		if branch: args.append(branch)

		self.git_cmd(args)

	def test_push(self, remote=None, branch=None, force=False):
		args = ['push', '-n']
		if force: args.append('-f')
		if remote: args.append(remote)
		if branch: args.append(branch)

		(ret, out, err) = self.git_cmd(args, raise_errors=False)
		return not ret

	#TODO: doesn't work
	def branch_list(self, all=False):
		args = ['branch']
		if all:
			args.append('-a')

		return self.git_cmd(args).split()

	def ref_list(self):
		args = ['show-ref']
		return [r.split()[1][5:] for r in self.git_cmd(args).split('\n')]

	def branch_create(self, dst, src=None, force=False):
		args = ['branch']
		if force:
			args.append('-f')
		args.append(dst)
		if src:
			args.append(src)

		self.git_cmd(args)

	def branch_delete(self, dst, force=False):
		args = ['branch']
		if force:
			args.append('-D')
		else:
			args.append('-d')
		args.append(dst)

		self.git_cmd(args)

	def checkout(self, branch, force=False):
		args = ['checkout', branch]
		if force:
			args.append('-f')

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
		args.append(branch)
		self.git_cmd(args)

	def update_ref(self, ref, newval):
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
		args.append(base)

		return self.git_cmd(args, raise_errors=False, print_output=False)

	#Query functions
	def status(self, porcelain=True):
		#TODO: parse status output, or leave as text?
		args = ['status']
		if porcelain:
			args.append('--porcelain')

		return self.git_cmd(args, raise_errors=True, print_output=False)

	def rev_parse(self, rev):
		try:
			return self.git_cmd(['rev-parse', rev])
		except GitError as e:
			if e.args[0].find('unknown revision') > -1:
				raise UnknownRevisionError('Unknown revision %s' % rev)
			else:
				raise e

	def valid_ref(self, ref, include_sha=True):
		if include_sha:
			try:
				self.rev_parse(ref)
				return True
			except UnknownRevisionError:
				return False
		else:
			#TODO: got to be a better way
			#there is: use show to show the ref, parse the first word of the response
			#(should be 'commit').  If !include_sha, verify !self.valid_sha(ref)
			refs = self.ref_list()
			return (ref in refs) or (('heads/' + ref) in refs) or \
				(('tags/' + ref) in refs) or (('remotes/' + ref) in refs)

	def valid_sha(self, ref):
		#TODO: got to be a better way
		#There is: check .git/objects/xx/xxxxxx..., verify that it's a 'commit' with show
		return (not self.valid_ref(ref, False)) and self.valid_ref(ref, True)

	def merge_base(self, rev1, rev2):
		return self.git_cmd(['merge-base', rev1, rev2])

	def symbolic_ref(self, ref):
		return self.git_cmd(['symbolic-ref', ref])

	def can_fastforward(self, merge_head, orig_head = 'HEAD'):
		return self.rev_parse(orig_head) == self.merge_base(orig_head, merge_head)

	def is_descendant(self, commit):
		return self.rev_parse(commit) in self.git_cmd(['rev-list', 'HEAD']).split()
