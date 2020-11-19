import argparse
import json
import csv
from collections import defaultdict

import googleapiclient
from googleapiclient import discovery
import requests

from counter_speech_bot.rate_limiter import RateLimiter


PERSPECTIVE_API_KEY = 'PERSPECTIVE_API_KEY'
TWITTER_CONSUMER_KEY = 'TWITTER_CONSUMER_KEY'
TWITTER_CONSUMER_SECRET = 'TWITTER_CONSUMER_SECRET'
TWITTER_BEARER_TOKEN = 'TWITTER_BEARER_TOKEN'


class CounterSpeechBot:

    def __init__(self, args):
        self.get_api_keys()
        self.tweet_limit = args.tweet_limit
        self.attributes = args.attributes
        self.service = discovery.build(
            'commentanalyzer', 'v1alpha1', developerKey=self.api_keys[PERSPECTIVE_API_KEY]
        )
        self.error_types_count = defaultdict(lambda: 0)

    def get_api_keys(self):
        self.api_keys = {}
        with open('.api_keys', 'r') as f:
            for name, value in csv.reader(f, delimiter='='):
                self.api_keys[name] = value

    def get_toxicity(self, tweet):
        # API documentation: https://support.perspectiveapi.com/s/about-the-api-methods
        request = {
            'comment': {
                'text': tweet['data']['text'],
            },
            'requestedAttributes': {attribute: {} for attribute in self.attributes},
        }

        try:
            return self.service.comments().analyze(body=request).execute()
        except googleapiclient.errors.HttpError as e:
            # weirdly the error_details aren't set on the error object until after `_get_reason` is called
            e._get_reason()
            error_type = e.error_details[0]['errorType']
            self.error_types_count[error_type] += 1
            print(f"- Skipping due to {error_type} error in Perspective API")
            return None

    def sample_realtime_tweets(self):
        """
        Returns an iterator of approximately 1% of realtime tweets
        API Documentation: https://developer.twitter.com/en/docs/twitter-api/tweets/sampled-stream/api-reference/get-tweets-sample-stream
        """
        url = 'https://api.twitter.com/2/tweets/sample/stream?tweet.fields=lang'
        headers = {'Authorization': f"Bearer {self.api_keys[TWITTER_BEARER_TOKEN]}"}
        print(f"Sampling 1% of realtime tweets...")
        response = requests.get(url, headers=headers, stream=True)
        if response.encoding is None:
            response.encoding = 'utf-8'

        return response.iter_lines(decode_unicode=True)

    def main(self):
        rate_limiter = RateLimiter(max_calls_per_second=1)
        tweet_count = 0
        for tweet in self.sample_realtime_tweets():
            if tweet_count >= self.tweet_limit:
                break

            tweet = json.loads(tweet)
            if tweet['data']['lang'] != 'en':
                continue
            rate_limiter.wait()
            print(f"Tweet: {tweet}")
            response = self.get_toxicity(tweet)
            if response:
                for attribute in self.attributes:
                    print(f"- {attribute}: {response['attributeScores'][attribute]['summaryScore']['value']}")
            tweet_count += 1

        print('Done!')
        print(f"Processed {tweet_count} tweets.")
        print(f"Total errors encountered: {sum(self.error_types_count.values())}")
        for error_type, count in self.error_types_count.items():
            print(f"- {len(count)} {error_type} errors")


if __name__ == '__main__':
    """
    Example command:
    python -m main --atributes TOXICITY IDENTITY_ATTACK INSULT
    """
    parser = argparse.ArgumentParser(description='Samples 1% of realtime tweets and scores them according to toxicity attributes from the Perspective API')
    parser.add_argument('--tweet-limit', default=None, type=int, help='Quit when the specified number of tweets have been processed.')
    parser.add_argument(
        '--attributes',
        nargs='+',
        default=['TOXICITY', 'IDENTITY_ATTACK'],
        help='List of attributes to analyze for each tweet. See https://support.perspectiveapi.com/s/about-the-api-attributes-and-languages\n'
             'default: TOXICITY IDENTITY_ATTACK',
    )
    args = parser.parse_args()
    CounterSpeechBot(args).main()
