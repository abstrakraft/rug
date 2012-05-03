import sys

import project

def main():
	p = project.Project.find_project()
	p.manifest_repo.gitk(*sys.argv[1:])

if __name__ == '__main__':
	main()
