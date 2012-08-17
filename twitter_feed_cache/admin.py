from django.contrib import admin
from django import forms
import requests

from models import FollowAccount, Tweet

class FollowAccountModelForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(FollowAccountModelForm, self).__init__(*args, **kwargs)

        self.fields["external_user_id"].widget.attrs["readonly"] = True
        self.fields["external_user_id"].widget.attrs["disabled"] = True
        self.fields["profile_image_url"].widget.attrs["readonly"] = True
        self.fields["profile_image_url"].widget.attrs["disabled"] = True

    def clean(self):
        screen_name = self.cleaned_data.get("screen_name")

        if not screen_name:
            raise forms.ValidationError("Screen Name missing.  You must enter a Screen Name.")

        try:
            # get id and profile_url based on screen_name
            url = "https://api.twitter.com/1/users/lookup.json?screen_name=%s" % screen_name
            response = requests.get(url)

            data = response.json

            if "error" in data:
                raise forms.ValidationError("Twitter's rate limit exceeded.  Try again in an hour.")
            else:
                self.cleaned_data["external_user_id"] = data[0]["id"]
                self.cleaned_data["profile_image_url"] = data[0]["profile_image_url"]
        except forms.ValidationError:
            # rethrow validation errors
            raise
        except:
            raise forms.ValidationError("Unable to find Screen Name on Twitter.  Double-check that is correct.  If the problem persists, inform the development team.")

        return self.cleaned_data


class FollowAccountModelAdmin(admin.ModelAdmin):
    form = FollowAccountModelForm

    list_display = ("screen_name", "active")
    fields = ("screen_name", "external_user_id", "profile_image_url", "active")

class TweetModelAdmin(admin.ModelAdmin):
    list_display_links = ("text",)
    list_display = ("posted_by_screen_name", "text", "created_at", "in_reply_to_screen_name")
    ordering = ("-created_at",)

# Register the Post Manager admin
admin.site.register(FollowAccount, FollowAccountModelAdmin)
admin.site.register(Tweet, TweetModelAdmin)