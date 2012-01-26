import sys
import getopt
import os.path
from project import Project, RugError
import buffer

def init(output, optdict={}, project_dir=None):
	Project.init(project_dir, optdict.has_key('-b'), output=output)

def clone(output, optdict={}, url=None, project_dir=None, remote=None, revset=None):
	if not url:
		raise RugError('url must be specified')

	Project.clone(url=url, project_dir=project_dir, remote=remote, revset=revset, bare=optdict.has_key('-b'), output=output)

def checkout(proj, optdict={}, rev=None):
	proj.checkout(rev)

def fetch(proj, optdict={}, repos=None):
	proj.fetch(repos)

def update(proj, optdict={}, repos=None):
	proj.update(repos)

def status(proj, optdict={}):
	return proj.status()

def revset(proj, optdict={}, dst=None, src=None):
	if dst is None:
		return proj.revset()
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

def publish(proj, optdict={}, remote=None):
	proj.publish(remote)

def remote_list(proj, optdict={}):
	return proj.remote_list()

def remote_add(proj, optdict={}, remote=None, fetch=None):
	proj.remote_add(remote, fetch)

#(function, pass project flag, options)
rug_commands = {
	'init': (init, False, 'b'),
	'clone': (clone, False, 'b'),
	'checkout': (checkout, True, ''),
	'fetch': (fetch, True, ''),
	'update': (update, True, ''),
	'status': (status, True, ''),
	'revset': (revset, True, ''),
	'add': (add, True, ''),
	'commit': (commit, True, ''),
	'publish': (publish, True, ''),
	'remote_list': (remote_list, True, ''),
	'remote_add': (remote_add, True, ''),
	#'reset': (Project.reset, True, ['soft', 'mixed', 'hard']),
	}

def main():
	if (len(sys.argv) < 2) or not rug_commands.has_key(sys.argv[1]):
		#TODO: write usage
		print 'rug usage'
	else:
		(func, pass_project, optspec) = rug_commands[sys.argv[1]]
		[optlist, args] = getopt.gnu_getopt(sys.argv[2:], optspec)
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
