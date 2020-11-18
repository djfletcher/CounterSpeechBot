import argparse
import json
import csv
from collections import defaultdict

import googleapiclient
from googleapiclient import discovery

from counter_speech_bot.rate_limiter import RateLimiter


PERSPECTIVE_API_KEY = 'PERSPECTIVE_API_KEY'
TWITTER_CONSUMER_KEY = 'TWITTER_CONSUMER_KEY'
TWITTER_CONSUMER_SECRET = 'TWITTER_CONSUMER_SECRET'
TWITTER_BEARER_TOKEN = 'TWITTER_BEARER_TOKEN'


class CounterSpeechBot:

    def __init__(self, args):
        self.get_keys()
        self.attributes = args.attributes
        self.service = discovery.build('commentanalyzer', 'v1alpha1', developerKey=self.api_keys[PERSPECTIVE_API_KEY])
        self.error_types_count = defaultdict(lambda: 0)

    def get_keys(self):
        self.api_keys = {}
        with open('.api_keys', 'r') as f:
            for name, value in csv.reader(f, delimiter='='):
                self.api_keys[name] = value

    def get_toxicity(self, request):
        try:
            return self.service.comments().analyze(body=request).execute()
        except googleapiclient.errors.HttpError as e:
            # weirdly the error_details aren't set on the error object until after this is called
            e._get_reason()
            error_type = e.error_details[0]['errorType']
            self.error_types_count[error_type] += 1
            print(f"- Skipping due to {error_type} error in Perspective API")
            return None

    def build_request(self, text):
        # API documentation: https://support.perspectiveapi.com/s/about-the-api-methods
        return {
            'comment': {
                'text': text,
            },
            'requestedAttributes': {attribute: {} for attribute in self.attributes},
        }

    def sample_realtime_tweets(self):
        # TODO
        return iter([])

    def main(self):
        rate_limiter = RateLimiter(max_calls_per_second=1)
        print(f"Sampling 1% of realtime tweets...")
        for tweet in self.sample_realtime_tweets():
            rate_limiter.wait()
            print(f"Tweet: {tweet}")
            request = self.build_request(tweet)
            response = self.get_toxicity(request)
            if response:
                for attribute in self.attributes:
                    print(f"- {attribute}: {response['attributeScores'][attribute]['summaryScore']['value']}")

        print('Done!')
        print(f"Total errors encountered: {sum(self.error_types_count.values())}")
        for error_type, count in self.error_types_count.items():
            print(f"- {len(count)} {error_type} errors")


if __name__ == '__main__':
    """
    Example command:
    python -m main --atributes TOXICITY IDENTITY_ATTACK INSULT
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--attributes',
        nargs='+',
        default=['TOXICITY', 'IDENTITY_ATTACK'],
        help='List of attributes to analyze for each tweet. See https://support.perspectiveapi.com/s/about-the-api-attributes-and-languages',
    )
    args = parser.parse_args()
    CounterSpeechBot(args).main()
