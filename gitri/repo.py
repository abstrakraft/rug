#TODO: stuck here because of circular dependency.
#find a fix and move this out
class Repo(object):
	def __init__(self, dir):
		from project import Project
		self.project = Project(dir)
		
		p = self.project
		mr = self.project.manifest_repo
		delegated_methods = {
			'valid_repo': p.valid_project,
			'valid_sha': mr.valid_sha,
			'valid_ref': mr.valid_ref,
			'update_ref': mr.update_ref,
			'head': mr.head,
			'rev_parse': mr.head,
			'symbolic_ref': mr.symbolic_ref,
			'is_descendant': mr.is_descendant,
			'can_fastforward': mr.can_fastforward,
			'remote_list': mr.remote_list,
			'remote_add': mr.remote_add,
			'remote_set_url': mr.remote_set_url,
			'remote_set_head': mr.remote_set_head,
			'branch': p.revset,
			'branch_create': p.revset_create,
			'status': p.status,
			'checkout': p.checkout,
			'commit': p.commit,
			'fetch': p.fetch,
			'push': p.publish,
			'test_push': p.test_publish,
			'merge': None, #TODO
			'dirty': None, #TODO
			'rebase': None, #TODO
		}

		self.__dict__.update(delegated_methods)
