import sys
import getopt
import os.path
from project import Project, RugError
import buffer

def init(output, optdict={}, project_dir=None):
	Project.init(project_dir, optdict.has_key('--bare'), output=output)

def clone(output, optdict={}, url=None, project_dir=None):
	if not url:
		raise RugError('url must be specified')

	Project.clone(url=url, project_dir=project_dir, source=optdict.get('-o'), revset=optdict.get('-b'), bare=optdict.has_key('--bare'), output=output)

def checkout(proj, optdict={}, rev=None, src=None):
	if '-b' in optdict:
		proj.revset_create(rev, src)
	proj.checkout(rev)

def fetch(proj, optdict={}, repos=None):
	proj.fetch(repos=repos)

def update(proj, optdict={}, repos=None):
	proj.update(repos)

def status(proj, optdict={}):
	return proj.status()

def revset(proj, optdict={}, dst=None, src=None):
	if dst is None:
		return proj.revset().get_short_name()
	else:
		proj.revset_create(dst, src)

def add(proj, optdict={}, project_dir=None, name=None, remote=None, rev=None, vcs=None):
	if not project_dir:
		raise RugError('unspecified directory')

	#Command-line interprets relative to cwd,
	#but python interface is relative to project root
	abs_path = os.path.abspath(project_dir)
	path = os.path.relpath(abs_path, proj.dir)
	proj.add(path, name, remote, rev, vcs)

def commit(proj, optdict={}, message=None):
	if not message:
		raise NotImplementedError('commit message editor not yet implemented') #TODO

	proj.commit(message)

def publish(proj, optdict={}, source=None):
	proj.publish(source)

def remote_list(proj, optdict={}):
	return '\n'.join(proj.remote_list())

def remote_add(proj, optdict={}, remote=None, fetch=None):
	proj.remote_add(remote, fetch)

def source_list(proj, optdict={}):
	return '\n'.join(proj.source_list())

def source_add(proj, optdict={}, source=None, url=None):
	proj.source_add(source, url)

#(function, pass project flag, options, long_options)
rug_commands = {
	'init': (init, False, '', ['--bare']),
	'clone': (clone, False, 'b:o:', ['--bare']),
	'checkout': (checkout, True, 'b', []),
	'fetch': (fetch, True, '', []),
	'update': (update, True, '', []),
	'status': (status, True, '', []),
	'revset': (revset, True, '', []),
	'add': (add, True, '', []),
	'commit': (commit, True, '', []),
	'publish': (publish, True, '', []),
	'remote_list': (remote_list, True, '', []),
	'remote_add': (remote_add, True, '', []),
	'source_list': (source_list, True, '', []),
	'source_add': (source_add, True, '', []),
	#'reset': (Project.reset, True, ['soft', 'mixed', 'hard']),
	}

def main():
	if (len(sys.argv) < 2) or not rug_commands.has_key(sys.argv[1]):
		#TODO: write usage
		print 'rug usage'
	else:
		(func, pass_project, optspec, long_options) = rug_commands[sys.argv[1]]
		[optlist, args] = getopt.gnu_getopt(sys.argv[2:], optspec, long_options)
		optdict = dict(optlist)
		output = buffer.Buffer()
		if pass_project:
			ret = func(Project.find_project(output=output), optdict, *args)
		else:
			ret = func(output, optdict, *args)

		out = output.get_buffer()
		if ret is not None:
			#if the function returned anything (even ""), that's the stdout, and anything in the
			#output buffer is stderr
			if out:
				sys.stderr.write(out)
			print ret
		elif out:
			#if the function doesn't return anything, output buffer is stdout, unless empty
			print out

if __name__ == '__main__':
	main()
