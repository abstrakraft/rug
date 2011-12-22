# rug terminology

- a rug **project** is a set of named sets of files (**repositories**)...
  - _the state of which is managed in a special file, called the __manifest__
    file, arguably the only novel work done in a project_
  - _which describes how the latent potential of a **NASCENT** project would be
    **manifested**_ 
- at a set of **remote** locations...
  - _pretty much URIs, but maybe URLs_
- where the project and repos are at a given **revision**, and have complete
  history available 
   - _where we're calling a project's revision a **revset**. seems better than 
     **george**._
  - _a revisions/revset can be identified by a cryptographic **hash** or 
    **tag**..._
     - _which is nice, as it is easy to understand what its meaning of the file
       tree would be created_
    - _or a named **branch**_
      - _using a named branch means a change will almost always be **PUSHABLE**,
        but doesn't guarantee cryptographically verifiable reproducibility_
         - _it might be appropriate for things that are accretative, like..._
             - _lists of tasks_
             - _test results_
- which, when all brought together locally, can be **repeatably** **realized** 
  as a tree of files.
  - _where realizing will be copying [TODO: symlinking, compiling, running 
    arbitrary scripts, conversion etc.]_
- that can be **locally modified**...
   - _so that you can develop, try things out, and still get back to known good 
     states_ 
- then **pushed back** to where they came from 
  - _broadly assuming that if you can push back to same remote repos you got the
    project data from, then others will be able to get your changes as well_
  - _though if you get into trouble and are irreconcilably **DIVERGENT** you 
    might have to **fork a repo**, or if you can't create new 
    repositories/branches at the same remotes, **fork a whole project**_
- in a way that is **not totally insane**


 
# state flow
```
+---------+                                                         +--------+
|      {s}|  clone  +---------+  manifest                  fetch    |     {s}|
| remote  +----+--->| NASCENT +--------------+----------------+-----+ remote |
| project |    |    +---------+              |                |     | repos  |
+---------+    |                             v                |     +--------+
   ^   ^       v                       +------------+         |        ^   ^
   |   :  +---------+                  | MANIFESTED |         |        :   |
   |   :  :      {s}:                  +-----+------+         v        :   |
   |   :  : local   :                        |            +-------+    :   |
   |   :  : project :                        |  checkout  :    {s}:    :   |
   |   :  +---------+                realize +------------+ local :    :   |
   |   :       ^                             |            : repos :    :   |
   |   :       |                             v            +-------+    :   |
   |   :       |                        +----------+          ^        :   |
   |   :       |                        | REALIZED |          |        :   |
   |   :       |                        +----+-----+          |        :   |
   |   :       |                      commit |                |        :   |
   |   :       |                             |                |        :   |
   |   :       +-----------------------------+----------------+        :   |
   |   :                                     |                         :   |
   |   :                                     V                         :   |
   |   :                               +-----------+                   :   |
   |   :                               | DIVERGENT |                   :   |
   |   :                               +-----+-----+                   :   |
   |   :                                  dry|run                      :   |
   |   +-------------------------------------|-------------------------+   |
   |                                         |                             |
   |                       +-----------------+----------------+            |
   |                       |fork project     |       fork repo|            |
   |                       v               ok|                v            |
   |                  +---------+            v            +--------+       |
   |                  | new  {s}|       +----------+      | new {s}|       |
   |                  | remote  |       | PUSHABLE |      | remote |       |
   |                  | project |       +----+-----+      | repos  |       |
   |                  +---------+        push|all         +--------+       |
   |                                         |                             |
   +-----------------------------------------+-----------------------------+
```

## Notation
- `{s}` is a repository
- `:` are actions without side-effects outside of your local environment
- a `+` at an intersection suggests a splitting while a `|` just means the
  diagram notation for ditaa (see below) wasn't saying the right thing

_Fun fact: some websites let you [edit][asciiflow] this format easily, 
[generate][ditaa] "real" images or [navigate][nh] dungeons_

[asciiflow]: http://www.asciiflow.com
[ditaa]: http://ditaa.org/ditaa/
[nh]: http://thegreatestgameyouwilleverplay.com/

