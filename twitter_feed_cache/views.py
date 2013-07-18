import json
from django.http import HttpResponse
from django.views.decorators.cache import cache_control

from content_utils.utils import format_date_short
from cachecow.pagecache import cache_page

from models import Tweet

@cache_page
@cache_control(max_age=1800)
def twitter_feed(request):
    tweets = Tweet.objects.all().order_by("-created_at")[0:10]

    feed = []
    for tweet in tweets:
        feed_tweet = {
            "external_tweet_id": str(tweet.external_tweet_id),
            "text": tweet.text,
            "created_at": tweet.created_at.strftime("%a %b %d %H:%M:%S +0000 %Y"),
            "created_at_custom": format_date_short(tweet.created_at),
            "posted_by": {
                "user_id": str(tweet.posted_by_user_id),
                "screen_name": tweet.posted_by_screen_name,
                "name": tweet.posted_by_name,
            },
        }

        if tweet.in_reply_to_user_id:
            feed_tweet["in_reply_to"] = {
                "user_id": str(tweet.in_reply_to_user_id),
                "screen_name": tweet.in_reply_to_screen_name,
                "status_id": str(tweet.in_reply_to_status_id),
            }

        feed.append(feed_tweet)

    return HttpResponse(json.JSONEncoder().encode(feed))