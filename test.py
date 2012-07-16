import rug
import unittest
import os
import shutil

test_url = 'https://github.com/abstrakraft/rug-test-project'
test_repo = 'test_repo'

class GitCloneTestCase(unittest.TestCase):
	'''Test cases for git.Repo.clone'''
	@classmethod
	def tearDownClass(cls):
		if os.path.exists(test_repo):
			shutil.rmtree(test_repo)

	def test_clone(self):
		'''test_clone - test git.Repo.clone with vanilla arguments'''
		repo = rug.git.Repo.clone(test_url, test_repo)
		self.assertEqual(repo.rev_parse('remotes/origin/master'), repo.rev_parse('master'))

class GitRevTestCase(unittest.TestCase):
	'''Test cases for git.Rev'''
	@classmethod
	def setUpClass(cls):
		rug.git.Repo.clone(test_url, test_repo)

	@classmethod
	def tearDownClass(cls):
		if os.path.exists(test_repo):
			shutil.rmtree(test_repo)

	def test_sha(self):
		'''test_rev - test the shas returned by various incantations of git.Rev'''
		repo=rug.git.Repo(test_repo)
		head=repo.head()
		self.assertEqual(rug.git.Rev(repo, head.get_short_name()).get_sha(), head.get_sha())
		self.assertEqual(rug.git.Rev(repo, head.get_long_name()).get_sha(), head.get_sha())
		self.assertEqual(rug.git.Rev(repo, head.get_sha()).get_sha(), head.get_sha())
		self.assertTrue(rug.git.Rev(repo, head.get_sha()).is_sha())

class RugCloneTestCase(unittest.TestCase):
	'''Test cases for rug.Project.clone'''
	@classmethod
	def tearDownClass(cls):
		if os.path.exists(test_repo):
			shutil.rmtree(test_repo)

	def test_clone(self):
		'''test_clone - test rug.Project.clone with vanilla arguments'''
		repo = rug.Project.clone(test_url, test_repo)

class RugInitTestCase(unittest.TestCase):
	'''Test cases for rug.Project.init'''
	@classmethod
	def tearDownClass(cls):
		if os.path.exists(test_repo):
			shutil.rmtree(test_repo)

	def test_init(self):
		'''test_init - test rug.Project.init with vanilla arguments'''
		repo = rug.Project.init(test_repo)

class RugOpsTestCase(unittest.TestCase):
	'''Various test cases for rug projects'''
	@classmethod
	def setUpClass(cls):
		rug.Project.clone(test_url, test_repo)

	@classmethod
	def tearDownClass(cls):
		if os.path.exists(test_repo):
			shutil.rmtree(test_repo)

	def test_add(self):
		rug.git.Repo.clone(test_url, os.path.join(test_repo, 'test'))
		p = rug.Project(test_repo)
		p.add('test')
		p.commit('test change')

if __name__ == '__main__':
	unittest.main()
