from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import datetime, timedelta

from twitter_feed_cache.models import Tweet

TWITTER_CACHE_EXPIRATION = getattr(settings, 'TWITTER_CACHE_EXPIRATION', 30)

class Command(BaseCommand):
    def handle(self, *args, **options):
        print "Performing cache maintenance"

        # Delete old tweets
        self.clear_old_tweets()

        print "Maintenance complete"

    def clear_old_tweets(self):
        '''
        Delete tweets older than TWITTER_CACHE_EXPIRATION days
        '''

        oldest_date = datetime.today() - timedelta(days=TWITTER_CACHE_EXPIRATION)

        tweets_to_delete = Tweet.objects.filter(created_at__lt=oldest_date)

        rows_affected = tweets_to_delete.count()

        tweets_to_delete.delete()

        print "Tweets deleted: " + str(rows_affected)