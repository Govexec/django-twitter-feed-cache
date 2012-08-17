from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = "Update local twitter feed cache based via Twitter API"

    def handle(self, *args, **options):
        from settings import TWITTER_USERNAME, TWITTER_PASSWORD
        import tweetstream

        from twitter_feed_cache.models import Tweet, FollowAccount
        import datetime


        users = []
        accounts = FollowAccount.objects.filter(active=True)
        for account in accounts:
            users.append(account.external_user_id)

        '''
        A note on parameters:

        track=words: This feature can be added.  It will receive tweets with the keywords provided in them.
        This can be used to find posts with specific hashtags (i.e. track=["#innovation",]).
        Note: it does NOT filter out tweets by "followed" (e.g. follow=users) users that don't contain the text.
        For that feature, we would have to implement filtering in our own DB queries.

        follow=users: This is a list of user IDs to be pulled into the stream.  The CMS automatically fetches ID based
        on screen_name.
        '''
        with tweetstream.FilterStream(TWITTER_USERNAME, TWITTER_PASSWORD, follow=users) as stream:
            for streamtweet in stream:
                if "delete" in streamtweet:
                    if streamtweet["delete"]["status"]["user_id"] in users:
                        print "Deleting tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (streamtweet["delete"]["status"]["user_id"], stream.count, stream.rate)

                        try:
                            tweet = Tweet.objects.get(external_tweet_id=streamtweet["delete"]["status"]["id"])
                            tweet.delete()
                        except:
                            print "Failed to delete"
                    else:
                        print "Bypassing delete tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (streamtweet["delete"]["status"]["user_id"], stream.count, stream.rate)
                elif streamtweet["user"]["id"] in users:
                    print "Saving tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (streamtweet["user"]["screen_name"], stream.count, stream.rate)
                    #print "Text: %s" % str(tweet["text"])

                    # Parse data
                    created_at = datetime.datetime.strptime(streamtweet["created_at"], '%a %b %d %H:%M:%S +0000 %Y')

                    # Add links to tweet
                    text = streamtweet["text"]
                    if "entities" in streamtweet:
                        if "user_mentions" in streamtweet["entities"]:
                            # reset already_processed
                            already_processed = []
                            for mention in streamtweet["entities"]["user_mentions"]:
                                if not mention["screen_name"] in already_processed:
                                    already_processed.append(mention["screen_name"])

                                    # replace @screen_name with link
                                    link = "<a href=\"http://www.twitter.com/%s\" rel=\"external\">@%s</a>" % (mention["screen_name"], mention["screen_name"])
                                    text = text.replace("@%s" % mention["screen_name"], link)

                        if "hashtags" in streamtweet["entities"]:
                            # reset already_processed
                            already_processed = []
                            for hashtag in streamtweet["entities"]["hashtags"]:
                                if not hashtag["text"] in already_processed:
                                    already_processed.append(hashtag["text"])

                                    # replace #hash_tag with link
                                    link = "<a href=\"https://twitter.com/search/?src=hash&q=%%23%s\" rel=\"external\">#%s</a>" % (hashtag["text"], hashtag["text"])
                                    text = text.replace("#%s" % hashtag["text"], link)

                        if "urls" in streamtweet["entities"]:
                            # reset already_processed
                            already_processed = []
                            for url in streamtweet["entities"]["urls"]:
                                if not url["display_url"] in already_processed:
                                    already_processed.append(url["display_url"])

                                    # replace #hash_tag with link
                                    link = "<a href=\"%s\" rel=\"external\" title=\"%s\">%s</a>" % (url["url"], url["expanded_url"], url["display_url"])
                                    text = text.replace(url["url"], link)

                    # Save tweet to DB
                    tweet = Tweet()

                    # Tweet data
                    tweet.external_tweet_id = streamtweet["id"]
                    tweet.text = text
                    tweet.created_at = created_at

                    # Posted by data
                    tweet.posted_by_user_id = streamtweet["user"]["id"]
                    tweet.posted_by_name = streamtweet["user"]["name"]
                    tweet.posted_by_screen_name = streamtweet["user"]["screen_name"]

                    # In reply to data
                    tweet.in_reply_to_user_id = streamtweet["in_reply_to_user_id"]
                    tweet.in_reply_to_screen_name = streamtweet["in_reply_to_screen_name"]
                    tweet.in_reply_to_status_id = streamtweet["in_reply_to_status_id"]

                    tweet.save()

                else:
                    print "Bypassing tweet from %-16s\t( tweet %d, rate %.1f tweets/sec)" % (streamtweet["user"]["screen_name"], stream.count, stream.rate)

        self.stdout.write("Stream stopped\n\n")