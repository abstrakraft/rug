import os
import sys

def dfs(info, path):
	ret = []
	for (d, c) in info[1].items():
		recurse_path = os.path.join(path, d)
		if c[0]:
			ret.append(recurse_path)
		else:
			ret.extend(dfs(c, recurse_path))
	return ret

def hierarchy(paths, fullpath=True):
	#TODO: properly handle ..
	path_split = map(lambda x:[s for s in x.split(os.path.sep) if s not in ['','.']], paths)

	#Trie/prefix tree approach
	#nodes are [path string for populated nodes, subdirectory dictionary (relpath->subnode)]
	#populated nodes correspond to populated paths.  since repos can be nested, this isn't the same
	#as leaves
	root = [None, {}]
	path_nodes = []

	for idx in range(len(paths)):
		cursor = root
		for d in path_split[idx]:
			prev_cursor = cursor
			if d in prev_cursor[1]:
				cursor = prev_cursor[1][d]
			else:
				cursor = [None, {}]
				prev_cursor[1][d] = cursor
		if cursor[0] is not None:
			raise ValueError('Duplicate paths: "%s" and "%s"' % (cursor[0], paths[idx]))
		else:
			cursor[0] = paths[idx]
			path_nodes.append(cursor)

	path_dict = {}
	for idx in range(len(paths)):
		if fullpath and paths[idx] != '.':
			init_path = paths[idx]
		else:
			init_path = ''
		path_dict[paths[idx]] = dfs(path_nodes[idx], init_path)

	return path_dict

if __name__ == '__main__':
	print hierarchy(sys.argv[1:])
