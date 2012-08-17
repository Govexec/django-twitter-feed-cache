from django.db import models

class FollowAccount(models.Model):
    screen_name = models.CharField(max_length=30)
    external_user_id = models.BigIntegerField(blank=True)
    profile_image_url = models.CharField(max_length=500, blank=True)
    active = models.BooleanField(default=True)

class Tweet(models.Model):
    # tweet
    external_tweet_id = models.BigIntegerField()
    text = models.CharField(max_length=2500)
    created_at = models.DateTimeField()

    # user
    posted_by_user_id = models.BigIntegerField()
    posted_by_screen_name = models.CharField(max_length=30)
    posted_by_name = models.CharField(max_length=200)

    # in reply to
    in_reply_to_screen_name = models.CharField(max_length=30, null=True)
    in_reply_to_user_id = models.BigIntegerField(null=True)
    in_reply_to_status_id = models.BigIntegerField(null=True)
