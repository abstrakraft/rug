import sys
import getopt
from project import Project

#(function, is_instance_func, options)
gitri_commands = {
	'clone': (Project.clone, False, ''),
	'checkout': (Project.checkout, True, ''),
	'fetch': (Project.fetch, True, ''),
	'update': (Project.update, True, ''),
	'status': (Project.status, True, ''),
	'revset': (Project.revset, True, ''),
	'add': (Project.add, True, ''),
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
