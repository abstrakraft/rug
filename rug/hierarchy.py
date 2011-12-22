import os
import sys

#info: (path (if any), parent, subdirectories, subdirectory info lists)
def dfs(info):
	ret = []
	for c in info[3]:
		if c[0]:
			ret.append(c[0])
		else:
			ret.extend(dfs(c))
	return ret

def hierarchy(paths):
	#TODO: properly handle ..
	path_split = map(lambda x:[s for s in x.split(os.path.sep) if s not in ['','.']], paths)

	root = [None, None, [], []]
	path_leaves = []

	for idx in range(len(paths)):
		cursor = root
		for d in path_split[idx]:
			try:
				cursor = cursor[3][cursor[2].index(d)]
			except ValueError:
				cursor[2].append(d)
				new_cursor = [None, cursor, [], []]
				cursor[3].append(new_cursor)
				cursor = new_cursor
		if cursor[0] is not None:
			raise ValueError('Duplicate paths: "%s" and "%s"' % (cursor[0], paths[idx]))
		else:
			cursor[0] = paths[idx]
			path_leaves.append(cursor)

	path_dict = {}
	for idx in range(len(paths)):
		path_dict[paths[idx]] = dfs(path_leaves[idx])

	return path_dict

if __name__ == '__main__':
	print hierarchy(sys.argv[1:])
