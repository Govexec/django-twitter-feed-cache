from distutils.core import setup

# Dynamically calculate the version based on twitter_feed_cache.VERSION
version_tuple = __import__('twitter_feed_cache').VERSION
version = '.'.join([str(v) for v in version_tuple])

setup(
    name='Twitter Feed Cache',
    version=version,
    author_email='GEWebDevTeam@govexec.com',
    packages=['twitter_feed_cache'],
    url='https://github.com/Govexec/django-twitter-feed-cache',
    description="Get public tweets from Twitter's Streaming API using tweetstream",
    long_description=open('README.rst').read(),
    install_requires=[
     "Django >= 1.3",
     "tweetstream",
    ]
)