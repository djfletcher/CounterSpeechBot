from collections import defaultdict
from pathlib import Path
from typing import Dict
from typing import NamedTuple
import argparse
import csv
import datetime
import json
import re

import googleapiclient
from googleapiclient import discovery
import requests

from counter_speech_bot.rate_limiter import RateLimiter


PERSPECTIVE_API_KEY = 'PERSPECTIVE_API_KEY'
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

        self.severe_toxicity_threshold = args.severe_toxicity_threshold
        self.identity_attack_threshold = args.identity_attack_threshold
        self.insult_threshold = args.insult_threshold
        self.sexually_explicit_exclusion_threshold = args.sexually_explicit_exclusion_threshold

        self.include_non_english = args.include_non_english
        self.tracking_file = self.create_tracking_file(args.tracking_file, args.append_to_existing_file)

        self.static_reply = args.static_reply
        self.dynamic_reply = args.dynamic_reply
        if self.dynamic_reply:
            raise Exception('The --dynamic-reply option is not yet supported. Please use --static-reply instead.')

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
        """ API documentation: https://support.perspectiveapi.com/s/about-the-api-methods """
        request = {
            'comment': {
                'text': self._strip_entities_from_text(tweet['data']['text']),
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

        def meets_threshold(analysis, attribute):
            # TODO: Generalize exclusion logic to be able to exclude any attributes instead of hardcoding it to sexual explicitness
            if attribute == 'SEXUALLY_EXPLICIT':
                arg_name = 'sexually_explicit_exclusion_threshold'
                threshold = getattr(self, arg_name)
                return self.get_attribute_score(analysis, attribute) < threshold
            else:
                arg_name = f"{attribute.lower()}_threshold"
                threshold = getattr(self, arg_name)
                return self.get_attribute_score(analysis, attribute) > threshold

        return all(meets_threshold(analysis, attribute) for attribute in self.attributes)

    def create_tracking_file(self, tracking_file, append_to_existing_file):
        if not tracking_file:
            tracking_file = f"toxic_tweets_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')}.txt"

        filepath = Path(tracking_file)
        if filepath.exists() and not append_to_existing_file:
            raise Exception(f"File already exists at {tracking_file}! Either remove the --tracking-file option or set --append-to-existing-file to true")

        filepath.touch()
        print(f"Created file to track toxic tweets at '{tracking_file}'")
        return tracking_file

    def track(self, toxic_tweet):
        self.toxic_tweets.append(toxic_tweet)
        reply = self.generate_reply(toxic_tweet)
        with open(self.tracking_file, 'a') as f:
            record = {**toxic_tweet._asdict(), 'potential_reply': reply}
            f.write(json.dumps(record) + '\n')

    def generate_reply(self, toxic_tweet):
        if self.static_reply:
            return self.static_reply
        return self.generate_dynamic_reply(toxic_tweet)

    def generate_dynamic_reply(self, toxic_tweet):
        # TODO
        raise NotImplementedError()

    def _format_tweet(self, tweet):
        author = tweet['includes']['users'][0]['name']
        text = tweet['data']['text']
        return f"{author} -> {text}"

    def _print_formatted_analysis(self, analysis, padding=''):
        for attribute in self.attributes:
            print(f"{padding}- {attribute}: {self.get_attribute_score(analysis, attribute)}")

    def _strip_entities_from_text(self, text):
        """
        - Removes the '#' hashtag prefix but keeps the hashtag text
        - Replaces all username handles with 'user'
        - Removes urls
        """
        text = text.replace('#', '')
        text = re.sub(r'@\w+', 'user', text)
        text = re.sub(r'http\S+', '', text)
        return text

    def process_realtime_stream(self):
        rate_limiter = RateLimiter(max_calls_per_second=1, padding_microseconds=1000)
        self.total_tweet_count = 0
        for tweet in self.sample_realtime_tweets():
            if (
                self.total_tweet_limit and self.total_tweet_count >= self.total_tweet_limit
                or self.toxic_tweet_limit and len(self.toxic_tweets) >= self.toxic_tweet_limit
            ):
                break

            try:
                tweet = json.loads(tweet)
            except json.decoder.JSONDecodeError as e:
                self.error_types_count['JSONDecodeEcrror'] += 1
                print(f"- Skipping due to JSONDecodeError")
                continue

            if tweet['data']['lang'] != 'en' and not self.include_non_english:
                continue

            print('------------------------------------------------')

            rate_limiter.wait()
            analysis = self.get_toxicity(tweet)
            if analysis and self.meets_thresholds(analysis):
                toxic_tweet = ToxicTweet(tweet, analysis)
                print("===================MEETS THRESHOLDS===================")
                print(self._format_tweet(tweet))
                self._print_formatted_analysis(analysis)
                print(f"\nPotential reply: '{self.generate_reply(toxic_tweet)}'")
                print("======================================================")
                self.track(toxic_tweet)
            else:
                print(self._format_tweet(tweet))

            self.total_tweet_count += 1

    def main(self):
        try:
            self.process_realtime_stream()
        except requests.exceptions.ChunkedEncodingError as e:
            self.error_types_count['ChunkedEncodingError'] += 1
            print(f"\n{e}")
            print('\nExiting due to broken connection to Twitter API')
        except KeyboardInterrupt:
            print('KeyboardInterrupt')

        print('\n\n\nSummary:')
        print(f"- Processed {self.total_tweet_count} tweets")
        print(f"- Identified {len(self.toxic_tweets)} toxic tweets:")
        for idx, toxic_tweet in enumerate(self.toxic_tweets):
            tweet, analysis = toxic_tweet
            print('------------------------------------------------')
            print(f"    {idx + 1} {self._format_tweet(tweet)}")
            self._print_formatted_analysis(analysis, padding='      ')
            print(f"\nPotential reply: '{self.generate_reply(toxic_tweet)}'")

        print('------------------------------------------------')
        if self.tracking_file:
            print(f"A record of these toxic tweets has been saved to '{self.tracking_file}'")

        print(f"- Encountered {sum(self.error_types_count.values())} errors:")
        for error_type, count in self.error_types_count.items():
            print(f"    - {count} - {error_type}")



if __name__ == '__main__':
    """
    Example command:
    python -m counter_speech_bot.realtime_bot --atributes TOXICITY IDENTITY_ATTACK INSULT --toxicity-threshold 0.75
    """
    parser = argparse.ArgumentParser(
        description='Randomly samples roughly 1% of publicly available tweets in real-time and scores them according to '
                    'toxicity attributes from the Perspective API'
    )
    parser.add_argument('--total-tweet-limit', default=None, type=int, help='Quit when the specified number of tweets have been processed.')
    parser.add_argument('--toxic-tweet-limit', default=None, type=int, help='Quit when the specified number of toxic tweets have been processed.')
    parser.add_argument(
        '--attributes',
        nargs='+',
        default=['SEVERE_TOXICITY', 'IDENTITY_ATTACK', 'SEXUALLY_EXPLICIT'],
        help='Space-separate list of attributes to analyze for each tweet. See https://support.perspectiveapi.com/s/about-the-api-attributes-and-languages for available attributes'
             ' | default: SEVERE_TOXICITY IDENTITY_ATTACK',
    )
    parser.add_argument('--severe-toxicity-threshold', default=0.5, type=float, help='Only process tweets whose severe toxicity is scored above this threshold. Must be a decimal between 0 and 1. | Default 0.5')
    parser.add_argument('--identity-attack-threshold', default=0.5, type=float, help='Only process tweets whose identity attack is scored above this threshold. Must be a decimal between 0 and 1. | Default 0.5')
    parser.add_argument('--insult-threshold', default=0.5, type=float, help='Only process tweets whose insult is scored above this threshold. Must be a decimal between 0 and 1. | Default 0.5')
    parser.add_argument('--sexually-explicit-exclusion-threshold', default=0.5, type=float, help='Only process tweets whose sexual explicitness is scored *below* this threshold. Must be a decimal between 0 and 1. | Default 0.5')
    parser.add_argument('--include-non-english', default=False, action='store_true', help='If true, includes tweets in all languages. By default, only english tweets are processed | Default: false')
    parser.add_argument('--tracking-file', default='', type=str, help='Path to and name of file to store tweets identified as toxic | Default: toxic_tweets_{start_timestamp}.txt')
    parser.add_argument('--append-to-existing-file', default=False, action='store_true', help='If true, appends new toxic tweets to an existing file. Requires --tracking-file | Default: false')
    parser.add_argument(
        '--static-reply',
        type=str,
        default='This comment could be considered an identity attack on a group of people',
        help='Log this as a potential reply to all toxic tweets | Default: `This comment could be considered an identity attack on a group of people`',
    )
    parser.add_argument('--dynamic-reply', default=False, action='store_true', help='**This flag is not yet supported**\nGenerate an intelligent, dynamic reply to toxic tweets based on the content of each tweet')

    args = parser.parse_args()
    CounterSpeechBot(args).main()
