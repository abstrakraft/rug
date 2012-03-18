import xml.dom.minidom
import StringIO

def read_from_string(s, default_default=None, apply_default=True):
	return read(StringIO.StringIO(s), default_default, apply_default)

def read(file_or_name, default_default=None, apply_default=True):
	manifest = xml.dom.minidom.parse(file_or_name)
	m = manifest.childNodes[0]
	if m.localName != 'manifest':
		raise RugError('malformed manifext.xml: no manifest element')

	#Defaults
	manifest_default = {}
	default_nodes = manifest.getElementsByTagName('default')
	#TODO: error on multiple default nodes?
	for node in default_nodes:
		manifest_default.update(node.attributes.items())
	if default_default is not None:
		default = {}
		default.update(default_default)
		default.update(manifest_default)
	else:
		default = manifest_default

	#Remotes
	remotes = {}
	remote_nodes = manifest.getElementsByTagName('remote')
	for node in remote_nodes:
		remote = dict(node.attributes.items())
		remotes[remote['name']] = remote

	#Repos
	repos = {}
	repo_nodes = sum(map(manifest.getElementsByTagName, ['repo', 'project']), [])
	for node in repo_nodes:
		if apply_default:
			repo = {}
			repo.update(default)
			repo.update(node.attributes.items())
		else:
			repo = dict(node.attributes.items())
		#TODO: detect duplicates
		repos[repo['path']] = repo

	if apply_default:
		return (remotes, repos)
	else:
		#manifest_default doesn't have the default_default entries, which we don't want to return anyway
		return (remotes, repos, manifest_default)

def write(filename, remotes, repos, default):
	doc = xml.dom.minidom.Document()
	manifest = doc.createElement('manifest')
	doc.appendChild(manifest)

	#Defaults
	default_node = doc.createElement('default')
	for (k,v) in sorted(default.items(), key=lambda x:x[0]):
		default_node.setAttribute(k,v)
	manifest.appendChild(default_node)

	#Remotes
	for remote in sorted(remotes.values(), key=lambda x:x['name']):
		remote_node = doc.createElement('remote')
		for (k,v) in sorted(remote.items(), key=lambda x:x[0]):
			remote_node.setAttribute(k,v)
		manifest.appendChild(remote_node)

	#Repos
	for repo in sorted(repos.values(), key=lambda x:x['name']):
		repo_node = doc.createElement('repo')
		for (k,v) in sorted(repo.items(), key=lambda x:x[0]):
			repo_node.setAttribute(k,v)
		manifest.appendChild(repo_node)

	f = open(filename, 'w')
	doc.writexml(f, newl='\n', addindent='\t')
	f.close()
