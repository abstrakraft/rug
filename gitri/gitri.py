import sys
import getopt
from project import Project, GitriError

def clone(optlist={}, url=None, dir=None, revset=None):
	if not url:
		raise GitriError('url must be specified')

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

def add(proj, optlist={}, dir=None):
	if not dir:
		raise GitriError('unspecified directory')

	return proj.add(dir)

def commit(proj, optlist={}, message=None):
	if not message:
		raise NotImplementedError('commit message editor not yet implemented') #TODO

	return proj.commit(message)

def publish(proj, optlist={}, remote=None):
	return proj.publish(remote)

#(function, pass project flag, options)
gitri_commands = {
	'clone': (clone, False, ''),
	'checkout': (checkout, True, ''),
	'fetch': (fetch, True, ''),
	'update': (update, True, ''),
	'status': (status, True, ''),
	'revset': (revset, True, ''),
	'add': (add, True, ''),
	'commit': (commit, True, ''),
	'publish': (publish, True, ''),
	#'reset': (Project.reset, True, ['soft', 'mixed', 'hard']),
	}

def main():
	if (len(sys.argv) < 2) or not gitri_commands.has_key(sys.argv[1]):
		#TODO: write usage
		print 'gitri usage'
	else:
		cmd = gitri_commands[sys.argv[1]]
		[optlist, args] = getopt.gnu_getopt(sys.argv[2:], cmd[2])
		if cmd[1]:
			ret = cmd[0](Project.find_project(), optlist, *args)
		else:
			ret = cmd[0](optlist, *args)

		if ret:
			print ret

if __name__ == '__main__':
	main()
