import rug, unittest

repo=rug.git.Repo.clone('git://github.com/ehawk61/Test_repo.git', 'cloned_repo')
head=repo.head()       	

class GtriUnitTestFunctions(unittest.TestCase):
	
	#TODO: Need a better explaination of the unit tests and what they accomplish. 
	
       	#test_cloneCheck is designed to check that the cloning operation works correctly thru checking the SHA's of the orginial repo against the cloned repo
	def test_cloneCheck(self):
		repo2=repo.clone('git://github.com/ehawk61/Test_repo.git', 'cloned_repo2')		
		self.assertEqual(repo.rev_parse('remotes/origin/master'), repo2.rev_parse('master'))

	#test_revCheck is designed to check that the Rev command works correctly by checking that using the different avialable methods will generate the SHA's correctly    
   	def test_revCheck(self):
		rev_repo=rug.git.Repo("cloned_repo2")
		rev_head=rev_repo.head()
		self.assertEqual(rug.git.Rev(rev_repo, rev_head.get_short_name()).get_sha(), rev_head.get_sha())
		self.assertEqual(rug.git.Rev(rev_repo, rev_head.get_long_name()).get_sha(), rev_head.get_sha())
		self.assertEqual(rug.git.Rev(rev_repo, rev_head.get_sha()).get_sha(), rev_head.get_sha())
		self.assertTrue(rug.git.Rev(rev_repo, rev_head.get_sha()).is_sha())	

		#Testing a branch outside of master 
		self.assertEqual(rug.git.Rev(repo, head.get_short_name()).get_sha(), head.get_sha())
		self.assertEqual(rug.git.Rev(repo, head.get_long_name()).get_sha(), head.get_sha())
		self.assertEqual(rug.git.Rev(repo, head.get_sha()).get_sha(), head.get_sha())
		self.assertTrue(rug.git.Rev(repo, head.get_sha()).is_sha())	

suite = unittest.TestLoader().loadTestsFromTestCase(GtriUnitTestFunctions)
unittest.TextTestRunner(verbosity=2).run(suite)
    
