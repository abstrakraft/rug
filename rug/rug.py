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

def status_recurse(project, project_status, level=0):
	indent = '  '
	output = []
	for (path, (stat, child_stat)) in project_status.items():
		r = project.wrappers[path]
		output.append('%2s  %s%s%s' % (stat, indent*level, level and '\\' or '', path))
		if r.vcs == 'rug':
			#subproject
			output += status_recurse(r.repo.project, child_stat, level+1)
		else:
			#repo
			for (file_path, s) in child_stat.items():
				output.append('%2s  %s%s%s' % (s, indent*(level+1), level and '\\' or '', file_path))

	return output

def status(proj, optdict):
	porcelain = optdict.has_key('-p')
	if porcelain:
		stat = proj.status(porcelain=True)
		return '\n'.join(status_recurse(proj, stat))
	else:
		return proj.status(porcelain=False)

def revset(proj, optdict, dst=None, src=None):
	if dst is None:
		return proj.revset().get_short_name()
	else:
		#TODO: this control branch returns nothing, causing "None" to be printed to the console
		#(src is None) is handled under the hood
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
	
def remove(proj, optdict, project_dir=None):
	if not project_dir:
		raise RugError('unspecified directory')

	#Command-line interprets relative to cwd,
	#but python interface is relative to project root
	abs_path = os.path.abspath(project_dir)
	path = os.path.relpath(abs_path, proj.dir)
	proj.remove(path=path)

def commit(proj, optdict):
	proj.commit(message=optdict.get('-m'), all=optdict.has_key('-a'), recursive=optdict.has_key('-r'))

def push(proj, optdict, source=None):
	if proj.push(source, test=True):
		proj.push(source)

def remote_list(proj, optdict):
	return '\n'.join(proj.remote_list())

def remote_add(proj, optdict, remote=None, fetch=None):
	proj.remote_add(remote, fetch)

def source_list(proj, optdict):
	return '\n'.join(proj.source_list())

def source_add(proj, optdict, source=None, url=None):
	proj.source_add(source, url)

def bind(proj, optdict):
	proj.bind(message=optdict.get('-m'), recursive=not optdict.has_key('-n'))

def merge_manifest(proj, optdict, *args):
	message = optdict.get('-m')
	do_merge_default = optdict.has_key('-d')
	rev = args[0]
	try:
		idx = args.index('--')
		paths = args[1:idx]
		remotes = args[idx+1:]
	except ValueError:
		paths = args[1:]
		remotes = []

	proj.merge_manifest(rev, message, do_merge_default, remotes, paths)

#(function, pass project flag, options, long_options, return_to_stdout)
rug_commands = {
	'init': (init, False, '', ['bare'], False),
	'clone': (clone, False, 'b:o:c:', ['bare'], False),
	'checkout': (checkout, True, 'b', [], False),
	'fetch': (fetch, True, '', [], False),
	'update': (update, True, 'r', [], False),
	'status': (status, True, 'p', [], True),
	'revset': (revset, True, '', [], True),
	'revset_list': (revset_list, True, '', [], True),
	'add': (add, True, 'sv:', [], False),
	'remove': (remove, True, '', [], False),
	'commit': (commit, True, 'm:ar', [], False),
	'push': (push, True, '', [], False),
	'remote_list': (remote_list, True, '', [], True),
	'remote_add': (remote_add, True, '', [], False),
	'source_list': (source_list, True, '', [], True),
	'source_add': (source_add, True, '', [], False),
	'bind': (bind, True, 'm:n', [], False),
	'merge_manifest': (merge_manifest, True, 'm:d', [], False),
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
			(func, pass_project, optspec, long_options, return_to_stdout) = rug_commands[command]
			[optlist, args] = getopt.gnu_getopt(sys.argv[2:], optspec, long_options)
			optdict = dict(optlist)
			if return_to_stdout:
				file = sys.stderr
			else:
				file = sys.stdout
			output_buffer = output.WriterOutputBuffer(output.FileWriter(file))
			if pass_project:
				ret = func(Project.find_project(output_buffer=output_buffer), optdict, *args)
			else:
				ret = func(output_buffer, optdict, *args)

			if return_to_stdout:
				print ret

if __name__ == '__main__':
	main()
