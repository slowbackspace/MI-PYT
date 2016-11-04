Library Usage
=============
.. testsetup::
   
   import pygithublabeler.run as l
   import os
   token = os.environ['GITHUB_TOKEN']

First import pygithublabeler
   
   >>> import pygithublabeler.run as labeler

Fetching issues
---------------
First create requests session with authorization headers

   >>> session = labeler.get_session(token)

Now fetch the issues from a repository

   >>> repository = labeler.get_repo("slowbackspace/testrepo")
   >>> issues = labeler.fetch_issues(session, repository)

You can also fetch issues comments

   >>> comments = []
   >>> for issue in issues:
   ...     comment = labeler.fetch_comments(session, repository, issue["number"])
   ...     comments.append(comment)

Rules and pattern matching
--------------------------
Let's define a few rules, a list of strings that will be searched for patterns and a fallback label that will be attached if no rule matches

   >>> rules = [
   ...     {"label": "bug", "pattern": ".*robot:bug.*"},
   ...     {"label": "question", "pattern": ".*robot:question.*"}
   ... ]
   >>> searched_content = ["Lorem ipsum dolor robot:bug sit"]
   >>> fallback_label = "wontfix" 

Finally lets find out what labels should be attached based on the defined rules

.. doctest::

   >>> labeler.check_rules(rules, searched_content, current_labels=[], fallback_label=fallback_label)
   (True, {'bug'})

Wohooo, we did it! The function returns a tuple with boolean that is True if some rule matched or False if there was no match. 
Second item in the tuple is set with labels to attach.

Now let's try if fallback label works.

.. doctest::

   >>> searched_content = ["Lorem ipsum dolor sit"]
   >>> labeler.check_rules(rules, searched_content, current_labels=[], fallback_label=fallback_label)
   (False, {'wontfix'})

and it works! There was no match and it returns the fallback label we set earlier.

Maybe you noticed we haven't play with the current_labels argument. Let's fix it.
We will define two strings, one that will match the bug rule and second that will match the question rule.
We will also set bug as a current label.

.. doctest::

   >>> searched_content = ["Lorem robot:bug sit", "Lorem ipsum robot:question dolor"]
   >>> labeler.check_rules(rules, searched_content, current_labels=["bug"], fallback_label=fallback_label)
   (True, {'question'})

Now we got a match and a single label to attach since the other label is already there.  

Attaching labels
----------------

Attaching labels is also easy. We can use the requests session and repository variables we defined in `Fetching issues`_.
We also need to specify issue's number.

   >>> missing_labels = ["bug"]
   >>> issue_number = 1
   >>> response = labeler.add_labels(session, repository, issue_number, missing_labels)
   Adding labels: ["bug"] to slowbackspace/testrepo on issue 1