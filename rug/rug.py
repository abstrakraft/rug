import sys
import getopt
from project import Project, RugError

def init(optlist={}, dir=None):
	return Project.init(dir)

def clone(optlist={}, url=None, dir=None, revset=None):
	if not url:
		raise RugError('url must be specified')

	return Project.clone(url, dir, revset)

def checkout(proj, optlist={}, rev=None):
	return proj.checkout(rev)

def fetch(proj, optlist={}, repos=None):
	return proj.fetch(repos)

def update(proj, optlist={}, repos=None):
	return proj.update(repos)

def status(proj, optlist={}):
	return proj.status()

def revset(proj, optlist={}, dst=None, src=None):
	if dst is None:
		return proj.revset()
	else:
		if src is None:
			return proj.revset_create(dst)
		else:
			return proj.revset_create(dst, src)

def add(proj, optlist={}, dir=None, name=None, remote=None):
	if not dir:
		raise RugError('unspecified directory')

	return proj.add(dir, name, remote)

def commit(proj, optlist={}, message=None):
	if not message:
		raise NotImplementedError('commit message editor not yet implemented') #TODO

	return proj.commit(message)

def publish(proj, optlist={}, remote=None):
	return proj.publish(remote)

def remote_list(proj, optlist={}):
	return proj.remote_list()

def remote_add(proj, optlist={}, remote=None, fetch=None):
	return proj.remote_add(remote, fetch)

#(function, pass project flag, options)
rug_commands = {
	'init': (init, False, ''),
	'clone': (clone, False, ''),
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
		if cmd[1]:
			ret = cmd[0](Project.find_project(), optlist, *args)
		else:
			ret = cmd[0](optlist, *args)

		if ret:
			print ret

if __name__ == '__main__':
	main()
