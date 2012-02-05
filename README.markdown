![The Rug](/abstrakraft/rug/raw/master/documentation/logo.png)
# The Rug #
_another repository of repositories implementation, inspired by [git-repo](http://code.google.com/p/git-repo), [ivy](http://ant.apache.org/ivy/) and others_

_note that this document is a plan of operation, and that most of the commands and workflows in it are not yet implemented_

_formerly known as gitri_

## Installing and Checking Out the Rug Test Project ##

	From the root of your rug repository (the directory containing this file), run

		python setup.py install

	Then, to clone the test repository, run

		rug clone https://github.com/abstrakraft/rug-test-project.git

## Nomenclature ##
- __repository__: a git (or other VCS) repository.  __repo__ is accepted shorthand.
- __project__: A collection of __repos__ in a specified layout.  A project is defined by a manifest __repo__.
- __revset__: A set of revisions of the __repos__ in a project.  They are named by the branch of the __project__ in which they are stored.

## Workflows ##

### New Project ####
use git to arrange repos and stuff

	rug init [dir]

adds repos to "index" = working copy of manifest

	rug add

publish changes to project

	rug publish

### Clone Project ###

	rug clone <url> [dir] [revset]
	rug checkout <revset>

### Track server changes ###
fetches from all repos, rebases or merges in all changes

	rug update

### Create a new revset to work a ticket ###
creates a new branch in manifest

	rug revset <new_revset> [source_revset]

use git to commit locally, change branches, etc.

	rug develop

update local manifest file

	rug add [-h|--hash|-b|--branch] <repo names>

commit local manifest file, push all repo branches and manifest branch

	rug publish

## Porcelain Commands ##
- `init` create a new rug project
- `clone` clone an existing rug project
- `update` update all repos with upstream updates (fetch followed by ?resetish command?)
- `checkout` checkout another revset
- `revset` create a new revset
- `add` add a repos branch or commit to the local manifest file
- `publish` push repo changes to servers (commit (manifest) followed by repo-push and manifest-push)
- `status` print status of all repos (--deep option for internal status)
- `fetch` fetch all repos
- `commit` commit everything necessary to checkout another revset, then check out the current one again, and get the same "stuff"

### Future Commands ###
- `reset` reset a subset of repos to the proper rug branch
- `merge` merge repos of other revsets into current one

### Project Layout ###
The .rug folder in the main repo contains the manifest repo.

For each revset, and in each repo, the following branches exist:

- `live` The name of the branch that should be checked out.  Note that this is really just a branch name - what that name happens to point to doesn't mean anything.
- `rug` Tracks the revset's local branch across checkouts.  This branch points to the sha that should become the live branch when the revset in question is checked out.
- `rug_index` Tracks the version of the revset's local branch that should be committed/published between checkouts.
- `bookmark` Tracks the remote branch as of the last commit.  Used to rebase changes on update if there is no bookmark_index.
- `bookmark_index` Tracks the remote branch as of the last update.  Used to rebase changes on update, if it exists.  This branch is used so that bookmark is unaltered until the revset is committed.

A more detailed branch name is required because there may be branches with the same name from different sources, revsets, and remotes.

Current philosophy is that development from different revsets with the same branches, should be separate.

## Branches ##
Checking out a revset for the first time creates the local rug branch (see above for naming convention).  Note that
two revsets that point to the same branch will have two local copies of that branch - this is by design.  In this way,
we implicitly maintain (committed, at least) local state of revsets between across checkouts.
Checking out subsequent times leaves the current branch and checks out the local rug branch.  Checkout options are passed straight
through to git.

A message should be printed indicating the last time the revset was fetched from the server, and any local changes to the revset.

Adding a repo records that branch name in the manifest.xml file.  Note that these changes are not maintained across revset checkouts, i.e.
adding, then checking out a revset (even the same one), then checking out the original revset reverts the branch to the local git branch.

Commit creates the proper local rug branch if the user is on another branch (see naming convention above - users may check out other
branches that are suffixes of that naming convention, and the correctly named branch will be created.  Existing rug branches will be
overwritten if they are ancestors of the new branch, otherwise an error will be thrown, or overriden with -f).  Changes to manifest.xml
are committed.

Push pushes all local branches, including the manifest branch (revset) to the appropriate server.

## Philosophy ##
Obviously, given the name, rug is meant to mimic git in some sense.  However, there are fundamental differences between managing "projects" and "repositories."
Some loose design guidelines:

1. Follow git when it makes sense.

2. Similarly, and important enough to state explicitly, don't follow git when it doesn't make sense.  Whether because git itself doesn't make sense, or because the design parameter in question simply doesn't map well to projects, doesn't matter.

3. Modifying repositores (committing, changing branches) requires (for now) knowledge of the underlying version control software (git).  However, a user should be able to clone a project and checkout various revsets, ALWAYS getting the correct thing (I'm referring to the quagmire that is fully-qualified branch names here), without any knowledge of the underlying vcs's.
