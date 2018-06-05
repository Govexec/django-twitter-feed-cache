import os
import time
import daemon
import signal
import lockfile
import datetime
from daemon.runner import make_pidlockfile, is_pidfile_stale
from optparse import make_option

from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.encoding import force_unicode
from django.core.management.base import BaseCommand, CommandError
import tweepy

from content_utils.utils import expire_cache_by_path
from twitter_feed_cache.models import Tweet, FollowAccount


TWITTER_CONSUMER_KEY = getattr(settings, 'TWITTER_CONSUMER_KEY', None)
TWITTER_CONSUMER_SECRET = getattr(settings, 'TWITTER_CONSUMER_SECRET', None)
TWITTER_ACCESS_TOKEN = getattr(settings, 'TWITTER_ACCESS_TOKEN', None)
TWITTER_ACCESS_SECRET = getattr(settings, 'TWITTER_ACCESS_SECRET', None)

TWITTER_CACHE_WORKING_DIR = getattr(settings, 'TWITTER_CACHE_WORKING_DIR', '/tmp')
TWITTER_CACHE_PID_FILE = os.path.realpath(getattr(settings, 'TWITTER_CACHE_PID_FILE', '/var/run/twitter_cache.pid'))
TWITTER_CACHE_LOG_FILE = os.path.realpath(getattr(settings, 'TWITTER_CACHE_LOG_FILE', None))
EPOCH_DATETIME = datetime.datetime(1970, 1, 1)
SECONDS_PER_DAY = 24 * 60 * 60


class Command(BaseCommand):
    pidfile_timeout = 10
    start_message = u"Started with pid %(pid)d"
    help = u"Update local twitter feed cache based via Twitter API"
    option_list = BaseCommand.option_list + (
        make_option('--start',
            action='store_true',
            dest='start',
            default=False,
            help='Start twitter feed cache as a daemon'),
        make_option('--stop',
            action='store_true',
            dest='stop',
            default=False,
            help='Stop twitter feed cache daemon'),
    )

    def handle(self, *args, **options):
        error_messages = []

        if TWITTER_CONSUMER_KEY is None:
            error_messages.append(u'settings.TWITTER_CONSUMER_KEY must be set.')

        if TWITTER_CONSUMER_SECRET is None:
            error_messages.append(u'settings.TWITTER_CONSUMER_SECRET must be set.')

        if TWITTER_ACCESS_TOKEN is None:
            error_messages.append(u'settings.TWITTER_ACCESS_TOKEN must be set.')

        if TWITTER_ACCESS_SECRET is None:
            error_messages.append(u'settings.TWITTER_ACCESS_SECRET must be set.')

        if len(error_messages) > 0:
            raise CommandError("\n".join(error_messages))

        if options['start']:
            self.start_daemon()
        elif options['stop']:
            self.stop_daemon()
        else:
            self.cache_tweets()

    def cache_tweets(self):
        users = FollowAccount.objects.filter(active=True)

        '''
        A note on parameters:

        track=words: This feature can be added.  It will receive tweets with the keywords provided in them.
        This can be used to find posts with specific hashtags (i.e. track=["#innovation",]).
        Note: it does NOT filter out tweets by "followed" (e.g. follow=users) users that don't contain the text.
        For that feature, we would have to implement filtering in our own DB queries.

        follow=users: This is a list of user IDs to be pulled into the stream.  The CMS automatically fetches ID based
        on screen_name.
        '''
        auth = tweepy.auth.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
        auth.set_access_token(TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET)
        api = tweepy.API(auth)

        for user in users:
            for streamtweet in api.user_timeline(user.screen_name):
                #import pdb;pdb.set_trace()
                if hasattr(streamtweet, "delete"):
                    if hasattr(streamtweet.delete, "status") and "user_id" in streamtweet["delete"]["status"]:
                        if streamtweet.delete.status.user_id in users:

                            # client.captureMessage(u"Deleting tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (streamtweet.delete.status.user_id, stream.count, stream.rate))
                            try:
                                tweet = Tweet.objects.get(external_tweet_id=int(streamtweet.delete.status.id))
                                tweet.delete()
                                expire_cache_by_path('/data/twitter_feed_cache/tweets/', is_view=False)
                            except Exception, err:
                                pass
                                # client.captureMessage(u"Failed to delete tweet: %s\n%s"
                                #    % (sys.exc_info()[0], str(err),))
                        else:
                            pass
                            # client.captureMessage("Bypassing delete tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (streamtweet.delete.status.user_id, stream.count, stream.rate))

                else:
                    user_screen_name = force_unicode(streamtweet.user.screen_name)
                    user_name = force_unicode(streamtweet.user.name)
                    # client.captureMessage(u"Saving tweet from %-16s" % (user_screen_name, ))

                    # Parse data
                    created_at = utc_to_local_datetime(streamtweet.created_at)

                    # Add links to tweet
                    text = mark_safe(streamtweet.text).encode('ascii','xmlcharrefreplace')
                    if hasattr(streamtweet, "entities") and streamtweet.entities:
                        if "user_mentions" in streamtweet.entities:
                            # reset already_processed
                            already_processed = []
                            for mention in streamtweet.entities["user_mentions"]:
                                mention["screen_name"] = force_unicode(mention["screen_name"])
                                if not mention["screen_name"] in already_processed:
                                    already_processed.append(mention["screen_name"])
                                    # replace @screen_name with link
                                    link = u"<a href=\"http://www.twitter.com/%s\" rel=\"external\">@%s</a>" % (mention["screen_name"], mention["screen_name"])
                                    text = text.replace(u"@%s" % mention["screen_name"], link)

                        if hasattr(streamtweet.entities, "hashtags") and streamtweet.entities.hashtags:
                            # reset already_processed
                            already_processed = []
                            for hashtag in streamtweet.entities.hashtags:
                                hashtag.text = force_unicode(hashtag.text)
                                if not hashtag.text in already_processed:
                                    already_processed.append(hashtag.text)
                                    # replace #hash_tag with link
                                    link = u"<a href=\"https://twitter.com/search/?src=hash&q=%%23%s\" rel=\"external\">#%s</a>" % (hashtag.text, hashtag.text)
                                    text = text.replace(u"#%s" % hashtag.text, link)

                        if "urls" in streamtweet.entities:
                            # reset already_processed
                            already_processed = []
                            for url in streamtweet.entities["urls"]:
                                if "display_url" in url and "url" in url and "expanded_url" in url:
                                    if url["display_url"] and url["url"] and url["expanded_url"]:
                                        url["display_url"] = force_unicode(url["display_url"])
                                        url["url"] = force_unicode(url["url"])
                                        url["expanded_url"] = force_unicode(url["expanded_url"])
                                        if not url["display_url"] in already_processed:
                                            already_processed.append(url["display_url"])
                                            # replace #hash_tag with link
                                            link = u"<a href=\"%s\" rel=\"external\" title=\"%s\">%s</a>" % (url["url"], url["expanded_url"], url["display_url"])
                                            text = text.replace(url["url"], link)

                    # If tweet exists, don't save twice
                    try:
                        tweet = Tweet.objects.get(external_tweet_id=int(streamtweet.id))
                    except:
                        tweet = Tweet()

                    # Save tweet to DB

                    # Tweet data
                    tweet.external_tweet_id = streamtweet.id
                    tweet.text = text
                    tweet.created_at = created_at
                    # Posted by data
                    tweet.posted_by_user_id = streamtweet.user.id
                    tweet.posted_by_name = user_name
                    tweet.posted_by_screen_name = user_screen_name
                    # In reply to data
                    tweet.in_reply_to_user_id = None if not streamtweet.in_reply_to_user_id else \
                        streamtweet.in_reply_to_user_id
                    tweet.in_reply_to_screen_name = None if not streamtweet.in_reply_to_screen_name else \
                        force_unicode(streamtweet.in_reply_to_screen_name)
                    tweet.in_reply_to_status_id = None if not streamtweet.in_reply_to_status_id else \
                        streamtweet.in_reply_to_status_id
                    # save tweet
                    tweet.save()

                    # clear cache for tweet feed
                    expire_cache_by_path('/data/twitter_feed_cache/tweets/', is_view=False)


        self.stdout.write(u"Stream stopped\n\n")

    """  Make a PIDLockFile instance """
    def init_pidfile(self):
        self.pidfile = make_pidlockfile(TWITTER_CACHE_PID_FILE, self.pidfile_timeout)


    """ Open the daemon context and run the application. """
    def start_daemon(self):
        # root user check
        if os.geteuid() == 0:
            raise CommandError(u"Can not run daemon as root!\n")
        # PID file setuo
        self.init_pidfile()
        # remove pid file if PID is not active
        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()
        # check for existence if PID file, means another instance is already running
        if self.pidfile.is_locked():
            pidfile_path = self.pidfile.path
            raise CommandError(u"PID file %(pidfile_path)r is locked.  Daemon is probably already running." % vars())
        # configure daemon context
        self.daemon_context = daemon.DaemonContext(
            working_directory=TWITTER_CACHE_WORKING_DIR,
            umask=0o002,
            detach_process=True,
            pidfile=self.pidfile
        )

        if TWITTER_CACHE_LOG_FILE is not None:
            self.daemon_context.stdout = open(TWITTER_CACHE_LOG_FILE, 'a+')
            self.daemon_context.stderr = open(TWITTER_CACHE_LOG_FILE, 'a+', buffering=0)

        self.stdout.write(u"Starting daemon...\n")

        try:
            # become a daemon
            self.daemon_context.open()
        except lockfile.AlreadyLocked:
            pidfile_path = self.pidfile.path
            raise CommandError(
                u"PID file %(pidfile_path)r already locked" % vars())
        except lockfile.LockTimeout:
            pidfile_path = self.pidfile.path
            raise CommandError(
                u"PID file %(pidfile_path)r lockfile.LockTimeout" % vars())

        pid = os.getpid()
        message = self.start_message % vars()
        self.emit_formatted_message(message)

        # run app
        self.cache_tweets()

    """ Terminate the daemon process specified in the current PID file. """
    def stop_daemon(self):
        # PID file setup
        self.init_pidfile()
        # does a PID file exists
        if not self.pidfile.is_locked():
            pidfile_path = self.pidfile.path
            raise CommandError(u"PID file %(pidfile_path)r not locked" % vars())
        # is the PID in the pid file active
        if is_pidfile_stale(self.pidfile):
            self.pidfile.break_lock()
            self.stdout.write(u"Daemon is not running.\n")
        else:
            # get the PID from PID file
            pid = self.pidfile.read_pid()
            try:
                # terminate the daemon process
                os.kill(pid, signal.SIGTERM)
            except OSError as exc:
                raise CommandError(u"Failed to terminate %(pid)d: %(exc)s" % vars())

            logfile = open(TWITTER_CACHE_LOG_FILE, 'a+', buffering=0)
            logfile.write(u"%s\tDaemon stopped\n" % datetime.datetime.now())
            logfile.close()
            self.stdout.write(u"Daemon stopped.\n")

def utc_to_local_datetime(utc_datetime):
    delta = utc_datetime - EPOCH_DATETIME
    utc_epoch = SECONDS_PER_DAY * delta.days + delta.seconds
    time_struct = time.localtime(utc_epoch)
    dt_args = time_struct[:6] + (delta.microseconds,)
    return datetime.datetime(*dt_args)
