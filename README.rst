=======
Twitter Feed Cache by GovExec
=======

Dependencies
------------

- tweetstream
- requests


Installation
------------
Add ``twitter_feed_cache`` to the ``INSTALLED_APPS`` in ``settings.py``::

    # settings.py
    INSTALLED_APPS = (
        ...
    	'twitter_feed_cache',
        ...
    )

Run::

$ python ./manage.py syncdb


Follow Users
------------
Add FollowAccounts in the admin.


Collect Tweets
------------
To collect tweets from the stream, run::

$ python ./manage.py update_twitter_feed_cache

To collect tweets from the stream as a daemon, run::

$ python ./manage.py update_twitter_feed_cache --start

To stop daemon, run::

$ python ./manage.py update_twitter_feed_cache --stop