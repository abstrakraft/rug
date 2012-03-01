import sys
import getopt
import os.path
from project import Project, RugError
import output
from version import __version__

def init(output_buffer, optdict, project_dir=None):
	Project.init(project_dir, optdict.has_key('--bare'), output_buffer=output_buffer)

def clone(output_buffer, optdict, url=None, project_dir=None):
	if not url:
		raise RugError('url must be specified')

	if optdict.has_key('-c'):
		repo_config = dict(map(lambda x: x.split('='), optdict['-c'].split(',')))
	else:
		repo_config = None

	Project.clone(
		url=url,
		project_dir=project_dir,
		source=optdict.get('-o'),
		revset=optdict.get('-b'),
		bare=optdict.has_key('--bare'),
	    repo_config=repo_config,
		output_buffer=output_buffer
	)

def checkout(proj, optdict, rev=None, src=None):
	if '-b' in optdict:
		proj.revset_create(rev, src)
	proj.checkout(rev)

def fetch(proj, optdict, repos=None):
	proj.fetch(repos=repos)

def update(proj, optdict):
	proj.update(recursive=optdict.has_key('-r'))

def status(proj, optdict):
	return proj.status(porcelain=optdict.has_key('-p'))

def revset(proj, optdict, dst=None, src=None):
	if dst is None:
		return proj.revset().get_short_name()
	else:
		proj.revset_create(dst, src)

def revset_list(proj, optdict):
	return '\n'.join(map(lambda rs: rs.get_short_name(), proj.revset_list()))

def add(proj, optdict, project_dir=None, name=None, remote=None, rev=None):
	if not project_dir:
		raise RugError('unspecified directory')

	vcs = optdict.get('-v')
	use_sha = optdict.has_key('-s')

	#Command-line interprets relative to cwd,
	#but python interface is relative to project root
	abs_path = os.path.abspath(project_dir)
	path = os.path.relpath(abs_path, proj.dir)
	proj.add(path=path, name=name, remote=remote, rev=rev, vcs=vcs, use_sha=use_sha)

def commit(proj, optdict):
	proj.commit(message=optdict.get('-m'), all=optdict.has_key('-a'), recursive=optdict.has_key('-r'))

def publish(proj, optdict, source=None):
	proj.publish(source)

def remote_list(proj, optdict):
	return '\n'.join(proj.remote_list())

def remote_add(proj, optdict, remote=None, fetch=None):
	proj.remote_add(remote, fetch)

def source_list(proj, optdict):
	return '\n'.join(proj.source_list())

def source_add(proj, optdict, source=None, url=None):
	proj.source_add(source, url)

#(function, pass project flag, options, long_options, return_stdout)
rug_commands = {
	'init': (init, False, '', ['--bare'], False),
	'clone': (clone, False, 'b:o:c:', ['--bare'], False),
	'checkout': (checkout, True, 'b', [], False),
	'fetch': (fetch, True, '', [], False),
	'update': (update, True, 'r', [], False),
	'status': (status, True, 'p', [], True),
	'revset': (revset, True, '', [], True),
	'revset_list': (revset_list, True, '', [], True),
	'add': (add, True, 'sv:', [], False),
	'commit': (commit, True, 'm:ar', [], False),
	'publish': (publish, True, '', [], False),
	'remote_list': (remote_list, True, '', [], True),
	'remote_add': (remote_add, True, '', [], False),
	'source_list': (source_list, True, '', [], True),
	'source_add': (source_add, True, '', [], False),
	#'reset': (Project.reset, True, ['soft', 'mixed', 'hard']),
	}

def main():
	if (len(sys.argv) < 2):
		#TODO: write usage
		print 'rug usage'
	else:
		command = sys.argv[1]
		if command == 'version':
			print 'rug version %s' % __version__
		elif command not in rug_commands:
			print 'rug usage'
		else:
			(func, pass_project, optspec, long_options, return_stdout) = rug_commands[command]
			[optlist, args] = getopt.gnu_getopt(sys.argv[2:], optspec, long_options)
			optdict = dict(optlist)
			if return_stdout:
				file = sys.stderr
			else:
				file = sys.stdout
			output_buffer = output.WriterOutputBuffer(output.FileWriter(file))
			if pass_project:
				ret = func(Project.find_project(output_buffer=output_buffer), optdict, *args)
			else:
				ret = func(output_buffer, optdict, *args)

			if return_stdout:
				print ret

if __name__ == '__main__':
	main()
