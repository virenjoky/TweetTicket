import re
import tweepy
import json
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy.streaming import StreamListener
from pymongo import MongoClient
import indicoio
from jira.client import JIRA
from datetime import datetime
 

class TwitterClient(object):
        '''
        Generic Twitter Class.
        '''
        def __init__(self):
                '''
                Class constructor or initialization method.
                '''
                # keys and tokens from the Twitter Dev Console
                consumer_key = 'gv69OHDKfXpocThtqGbt4ksDH'
                consumer_secret = 'ljzM7SsfiaO6TJTWs4fy97bMpyFlSG3UanMrDIofEPUXYEbeED'
                access_token = '923964019429466112-zClJUROPw7YqcLjD9YLsaAy4AzcfPce'
                access_token_secret = 'LSkP3AvEohNNPVYrbZEuKKgQn4jScQqGzWoCpsSS0XcUZ'

                # attempt authentication
                try:
                        # create OAuthHandler object
                        self.auth = OAuthHandler(consumer_key, consumer_secret)
                        # set access token and secret
                        self.auth.set_access_token(access_token, access_token_secret)
                        # create tweepy API object to fetch tweets
                        self.api = tweepy.API(self.auth)
                except:
                        print("Error: Twitter Authentication Failed")

                        
#This is a basic listener that just prints received tweets to stdout.
class StdOutListener(StreamListener):

        def on_data(self, data):
                full_tweet = json.loads(data)
                db_tweets_result = db.tweets.insert_one(full_tweet)
                parsed_tweet = {}
                # saving id of tweet
                parsed_tweet['id'] = full_tweet['id']
                # saving user of the tweet
                parsed_tweet['user'] = full_tweet['user']['screen_name']
                # saving text of tweet
                parsed_tweet['text'] = self.clean_tweet(full_tweet['text'])
                # saving sentiment of tweet
                sentiment_score = self.get_tweet_sentiment(full_tweet['text'])
                if sentiment_score > 0.5:
                        parsed_tweet['sentiment'] = 'positive'
                elif sentiment_score == 0.5:
                        parsed_tweet['sentiment'] = 'neutral'
                else:
                        parsed_tweet['sentiment'] = 'negative'
                parsed_tweet['score'] = sentiment_score 
                db_sentiment_result = db.sentiment.insert_one(parsed_tweet)
                if sentiment_score < 0.5:
                        jira_options={'server': 'https://sidjira.atlassian.net/'}
                        jira = JIRA(options=jira_options,basic_auth=('sidjira2017@gmail.com','ssap4321'))
                        searchString = 'project="MSD" and status!=done and summary~"' + full_tweet['user']['screen_name'] + '"'
                        try:
                                tickets = jira.search_issues(searchString)
                        except:
                                print('Error in searching Jira')
                        if tickets:
                                for ticket in tickets:
                                        try:
                                                comment = jira.add_comment(ticket,parsed_tweet['text'])
                                        except:
                                                print('add comment failed for ticket ', ticket.key)
                                return True
                        jiraSummary = 'Issue created by ' + full_tweet['user']['screen_name']
                        issue_dict = {
                                     'project': {'key': 'MSD'},
                                     'summary': jiraSummary,
                                     'description': parsed_tweet['text'],
                                     'issuetype': {'name': 'Problem'},
                                     'assignee': {'name': 'admin'},
                                     'priority': {'name': 'Medium'}
                                     }
                        try:
                                new_issue = jira.create_issue(fields=issue_dict)
                        except Exception as e:
                                print('Ticket creation failed for ', full_tweet['user']['screen_name'])
                                print(e)
                                return True
                        jira_data = {}
                        jira_data['user'] = full_tweet['user']['screen_name']
                        jira_data['ticket_key'] = new_issue.key
                        jira_data['timestamp']=str(datetime.now())
                        db_jirainfo_result = db.jirainfo.insert_one(jira_data)
                #print(parsed_tweet['text'],',',parsed_tweet['sentiment'])
                return True

        def on_error(self, status):
                print(status)

        def clean_tweet(self, tweet):
                '''
                Utility function to clean tweet text by removing links, special characters
                using simple regex statements.
                '''
                return ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", tweet).split())
                                                                        

        def get_tweet_sentiment(self, tweet):
                '''
                Utility function to classify sentiment of passed tweet
                using indicoio
                '''
                indicoio.config.api_key = 'e7cf4e703a29b6cdcecec19c5898185e'
                # calculate sentiment score
                myString = self.clean_tweet(tweet)
                if not bool(myString and myString.strip()):
                        return 0.5
                try:
                        sentiment_score = indicoio.sentiment_hq(myString)
                except:
                        print('connection issue with indicoio')
                        return 0.5
                if sentiment_score > 0.5:
                        sentiment = 'positive'
                elif sentiment_score == 0.5:
                        sentiment = 'neutral'
                else:
                        sentiment = 'negative'
                print(myString,",",sentiment)
                return sentiment_score



def main():
        # creating object of TwitterClient Class
        api = TwitterClient()
        # creating object for mongo connection
        client = MongoClient()
        # setting the database as twitterapp database
        global db 
        db = client.twitterapp
        # calling function to get tweets
        twitter_stream = Stream(api.auth, StdOutListener())
        twitter_stream.filter(track=['padmavati'])
        

        
if __name__ == "__main__":
        # calling main function
        main()
