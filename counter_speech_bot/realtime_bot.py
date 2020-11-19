import argparse
import json
import csv
from collections import defaultdict
from typing import NamedTuple
from typing import Dict

import googleapiclient
from googleapiclient import discovery
import requests

from counter_speech_bot.rate_limiter import RateLimiter


PERSPECTIVE_API_KEY = 'PERSPECTIVE_API_KEY'
TWITTER_CONSUMER_KEY = 'TWITTER_CONSUMER_KEY'
TWITTER_CONSUMER_SECRET = 'TWITTER_CONSUMER_SECRET'
TWITTER_BEARER_TOKEN = 'TWITTER_BEARER_TOKEN'


class ToxicTweet(NamedTuple):
    tweet: Dict[str, object]
    analysis: Dict[str, object]


class CounterSpeechBot:

    def __init__(self, args):
        self.get_api_keys()
        self.total_tweet_limit = args.total_tweet_limit
        self.toxic_tweet_limit = args.toxic_tweet_limit
        self.attributes = args.attributes
        self.toxicity_threshold = args.toxicity_threshold
        self.identity_attack_threshold = args.identity_attack_threshold
        self.insult_threshold = args.insult_threshold
        self.include_non_english = args.include_non_english

        self.service = discovery.build(
            'commentanalyzer', 'v1alpha1', developerKey=self.api_keys[PERSPECTIVE_API_KEY]
        )
        self.error_types_count = defaultdict(lambda: 0)
        # This tracks the tweets (with analysis) that meet the thresholds passed in
        self.toxic_tweets = []

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
            'spanAnnotations': True
        }

        try:
            return self.service.comments().analyze(body=request).execute()
        except googleapiclient.errors.HttpError as e:
            # weirdly the error_details aren't set on the error object until after `_get_reason` is called
            e._get_reason()
            error_type = e.error_details[0]['errorType']
            self.error_types_count[error_type] += 1
            print(self._format_tweet(tweet))
            print(f"- Skipping due to {error_type} error in Perspective API")
            return None

    def sample_realtime_tweets(self):
        """
        Returns an iterator of approximately 1% of realtime tweets
        API Documentation: https://developer.twitter.com/en/docs/twitter-api/tweets/sampled-stream/api-reference/get-tweets-sample-stream
        """
        tweet_fields = ['lang', 'entities']
        expansions = ['author_id']
        url = f"https://api.twitter.com/2/tweets/sample/stream?tweet.fields={','.join(tweet_fields)}&expansions={','.join(expansions)}"
        headers = {'Authorization': f"Bearer {self.api_keys[TWITTER_BEARER_TOKEN]}"}
        print(f"Sampling 1% of realtime tweets...")
        response = requests.get(url, headers=headers, stream=True)
        if response.encoding is None:
            response.encoding = 'utf-8'

        return response.iter_lines(decode_unicode=True)

    def get_attribute_score(self, analysis, attribute):
        """ Helper to get the score of a particular attribute from the perspective API response """
        return analysis['attributeScores'][attribute]['summaryScore']['value']

    def meets_thresholds(self, analysis):

        def is_above_threshold(analysis, attribute):
            arg_name = f"{attribute.lower()}_threshold"
            threshold = getattr(self, arg_name)
            return self.get_attribute_score(analysis, attribute) > threshold

        return all(is_above_threshold(analysis, attribute) for attribute in self.attributes)

    def _format_tweet(self, tweet):
        author = tweet['includes']['users'][0]['name']
        text = tweet['data']['text']
        return f"{author} -> {text}"

    def _print_formatted_analysis(self, analysis, padding=''):
        for attribute in self.attributes:
            print(f"{padding}- {attribute}: {self.get_attribute_score(analysis, attribute)}")

    def main(self):
        rate_limiter = RateLimiter(max_calls_per_second=1, padding_microseconds=1000)
        total_tweet_count = 0
        for tweet in self.sample_realtime_tweets():
            if (
                self.total_tweet_limit and total_tweet_count >= self.total_tweet_limit
                or self.toxic_tweet_limit and len(self.toxic_tweets) >= self.toxic_tweet_limit
            ):
                break

            try:
                tweet = json.loads(tweet)
            except json.decoder.JSONDecodeError as e:
                self.error_types_count['JSONDecodeError'] += 1
                print(f"- Skipping due to JSONDecodeError")
                continue

            if tweet['data']['lang'] != 'en' and not self.include_non_english:
                continue

            print('------------------------------------------------')

            rate_limiter.wait()
            analysis = self.get_toxicity(tweet)
            if analysis and self.meets_thresholds(analysis):
                print("===================MEETS THRESHOLDS===================")
                print(self._format_tweet(tweet))
                print(self._print_formatted_analysis(analysis))
                print("======================================================")
                # keep track of these
                self.toxic_tweets.append(ToxicTweet(tweet, analysis))
            else:
                print(self._format_tweet(tweet))

            total_tweet_count += 1

        print('\n\n\nSummary:')
        print(f"- Processed {total_tweet_count} tweets")
        print(f"- Identified {len(self.toxic_tweets)} toxic tweets:")
        for idx, (tweet, analysis) in enumerate(self.toxic_tweets):
            print('------------------------------------------------')
            print(f"    {idx + 1} {self._format_tweet(tweet)}")
            self._print_formatted_analysis(analysis, padding='      ')

        print(f"- Encountered {sum(self.error_types_count.values())} errors:")
        for error_type, count in self.error_types_count.items():
            print(f"    - {count} - {error_type}")


if __name__ == '__main__':
    """
    Example command:
    python -m main --atributes TOXICITY IDENTITY_ATTACK INSULT --toxicity-threshold 0.75
    """
    parser = argparse.ArgumentParser(
        description='Randomly samples roughly 1% of publicly available tweets in real-time and scores them according to '
                    'toxicity attributes from the Perspective API'
    )
    parser.add_argument('--total-tweet-limit', default=None, type=int, help='Quit when the specified number of tweets have been processed.')
    parser.add_argument('--toxic-tweet-limit', default=None, type=int, help='Quit when the specified number of toxic tweets have been processed.')
    parser.add_argument('--toxicity-threshold', default=0.0, type=float, help='Only process tweets whose toxicity is scored above this threshold')
    parser.add_argument('--identity-attack-threshold', default=0.0, type=float, help='Only process tweets whose identity attack is scored above this threshold')
    parser.add_argument('--insult-threshold', default=0.0, type=float, help='Only process tweets whose insult is scored above this threshold')
    parser.add_argument(
        '--attributes',
        nargs='+',
        default=['TOXICITY', 'IDENTITY_ATTACK'],
        help='List of attributes to analyze for each tweet. See https://support.perspectiveapi.com/s/about-the-api-attributes-and-languages\n'
             'default: TOXICITY IDENTITY_ATTACK',
    )
    parser.add_argument('--include-non-english', default=False, type=bool, help='If true, includes tweets in all languages. By default, only english tweets are processed.')
    args = parser.parse_args()
    CounterSpeechBot(args).main()
