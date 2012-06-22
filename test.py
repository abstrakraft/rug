import rug, unittest

class RugTestCase(unittest.TestCase):

	#TODO: Need a better explaination of the unit tests and what they accomplish. 

	url = 'git://github.com/abstrakraft/rug-test-project'

	#test_cloneCheck is designed to check that the cloning operation works correctly thru checking the SHA's of the orginial repo against the cloned repo
	def test_cloneCheck(self):
		repo = rug.git.Repo.clone(self.url, 'test_repo')
		self.assertEqual(repo.rev_parse('remotes/origin/master'), repo.rev_parse('master'))

	#test_revCheck is designed to check that the Rev command works correctly by checking that using the different avialable methods will generate the SHA's correctly
	def test_revCheck(self):
		repo=rug.git.Repo('test_repo')
		head=repo.head()
		self.assertEqual(rug.git.Rev(repo, head.get_short_name()).get_sha(), head.get_sha())
		self.assertEqual(rug.git.Rev(repo, head.get_long_name()).get_sha(), head.get_sha())
		self.assertEqual(rug.git.Rev(repo, head.get_sha()).get_sha(), head.get_sha())
		self.assertTrue(rug.git.Rev(repo, head.get_sha()).is_sha())

suite = unittest.TestLoader().loadTestsFromTestCase(RugTestCase)
unittest.TextTestRunner(verbosity=2).run(suite)
