import sys
import getopt
import os.path
from project import Project, RugError

def init(optdict={}, project_dir=None):
	return Project.init(project_dir, optdict.has_key('-b'))

def clone(optdict={}, url=None, project_dir=None, remote=None, revset=None):
	if not url:
		raise RugError('url must be specified')

	return Project.clone(url=url, project_dir=project_dir, remote=remote, revset=revset, bare=optdict.has_key('-b'))

def checkout(proj, optdict={}, rev=None):
	return proj.checkout(rev)

def fetch(proj, optdict={}, repos=None):
	return proj.fetch(repos)

def update(proj, optdict={}, repos=None):
	return proj.update(repos)

def status(proj, optdict={}):
	return proj.status()

def revset(proj, optdict={}, dst=None, src=None):
	if dst is None:
		return proj.revset()
	else:
		if src is None:
			return proj.revset_create(dst)
		else:
			return proj.revset_create(dst, src)

def add(proj, optdict={}, project_dir=None, name=None, remote=None, rev=None, vcs=None):
	if not project_dir:
		raise RugError('unspecified directory')

	#Command-line interprets relative to cwd,
	#but python interface is relative to project root
	abs_path = os.path.abspath(project_dir)
	path = os.path.relpath(abs_path, proj.dir)
	return proj.add(path, name, remote, rev, vcs)

def commit(proj, optdict={}, message=None):
	if not message:
		raise NotImplementedError('commit message editor not yet implemented') #TODO

	return proj.commit(message)

def publish(proj, optdict={}, remote=None):
	return proj.publish(remote)

def remote_list(proj, optdict={}):
	return proj.remote_list()

def remote_add(proj, optdict={}, remote=None, fetch=None):
	return proj.remote_add(remote, fetch)

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
		cmd = rug_commands[sys.argv[1]]
		[optlist, args] = getopt.gnu_getopt(sys.argv[2:], cmd[2])
		optdict = dict(optlist)
		if cmd[1]:
			ret = cmd[0](Project.find_project(), optdict, *args)
		else:
			ret = cmd[0](optdict, *args)

		if ret:
			print ret

if __name__ == '__main__':
	main()
