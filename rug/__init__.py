from project import Project
from repo import Repo
from version import __version__
import wrapper, git

wrapper.Wrapper.register_vcs('git', git.Repo)
wrapper.Wrapper.register_vcs('rug', Repo)
