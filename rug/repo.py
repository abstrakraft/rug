import project

class Repo_Rev(project.Revset):
	@staticmethod
	def find_repo(repo_finder):
		return repo_finder.project.manifest_repo

class Repo(object):
	valid_repo = project.Project.valid_project
	rev_class = Repo_Rev

	def __init__(self, repo_dir, output_buffer=None):
		from project import Project
		self.project = Project(repo_dir, output_buffer=output_buffer)

		p = self.project
		mr = self.project.manifest_repo
		delegated_methods = {
			'valid_sha': mr.valid_sha,
			'valid_rev': mr.valid_rev,
			'update_ref': mr.update_ref,
			'delete_ref': mr.delete_ref,
			'head': mr.head,
			'rev_parse': mr.rev_parse,
			'symbolic_ref': mr.symbolic_ref,
			'remote_list': p.source_list,
			'remote_add': p.source_add,
			'remote_set_url': p.source_set_url,
			'remote_set_head': p.source_set_head,
			'branch': p.revset,
			'branch_create': p.revset_create,
			'status': p.status,
			'checkout': p.checkout,
			'commit': p.commit,
			'fetch': p.fetch,
			'dirty': p.dirty,
			#'push': p.publish,
			#'test_push': p.test_publish,
			'merge': None, #TODO
			'rebase': None, #TODO
		}

		self.__dict__.update(delegated_methods)

	@classmethod
	def init(cls, repo_dir=None, output_buffer=None):
		project.Project.init(project_dir=repo_dir, output_buffer=output_buffer)
		return cls(repo_dir)

	@classmethod
	def clone(cls, url, repo_dir=None, remote=None, rev=None, config=None, output_buffer=None):
		project.Project.clone(url, project_dir=repo_dir, source=remote, revset=rev, repo_config=config, output_buffer=output_buffer)
		return cls(repo_dir)

	def fetch(self, remote=None):
		#TODO: repo Project doesn't currently support fetching a particular source
		self.project.fetch()

	def add_ignore(self, pattern):
		raise NotImplemented('ignoring through rug repos not implemented')

	def push(self, remote, branch, force):
		#TODO: this is a hack to drop the branch and force args, because rug repos don't handle them. Fix
		return self.project.publish(remote)

	def test_push(self, remote, branch, force):
		#TODO: this is a hack to drop the branch and force args, because rug repos don't handle them. Fix
		return self.project.test_publish(remote)

	def update(self, recursive=False):
		if self.project.dirty():
			self.project.checkout()
		self.project.update(recursive)

project.Project.register_vcs('rug', Repo)
