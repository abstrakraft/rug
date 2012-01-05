import project

class Repo(object):
	valid_repo = project.Project.valid_project

	def __init__(self, dir):
		from project import Project
		self.project = Project(dir)
		
		p = self.project
		mr = self.project.manifest_repo
		delegated_methods = {
			'valid_sha': mr.valid_sha,
			'valid_ref': mr.valid_ref,
			'update_ref': mr.update_ref,
			'head': mr.head,
			'rev_parse': mr.rev_parse,
			'symbolic_ref': mr.symbolic_ref,
			'is_descendant': mr.is_descendant,
			'can_fastforward': mr.can_fastforward,
			'remote_list': p.source_list,
			'remote_add': p.source_add,
			'remote_set_url': p.source_set_url,
			'remote_set_head': p.source_set_head,
			'branch': p.revset,
			'branch_create': p.revset_create,
			'status': p.status,
			'checkout': p.checkout,
			'commit': p.commit,
			'push': p.publish,
			'test_push': p.test_publish,
			'merge': None, #TODO
			'dirty': None, #TODO
			'rebase': None, #TODO
		}

		self.__dict__.update(delegated_methods)

	@classmethod
	def init(cls, dir=None):
		project.Project.init(dir=dir)
		return cls(dir)

	@classmethod
	def clone(cls, url, dir=None, remote=None, rev=None):
		project.Project.clone(url, dir=dir, remote=remote, revset=rev)
		return cls(dir)

	def fetch(self, remote=None):
		#TODO: repo Project doesn't currently support fetching a particular source
		self.project.fetch()

project.Project.register_vcs('rug', Repo)
