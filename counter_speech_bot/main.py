import argparse
import json
from collections import defaultdict

import googleapiclient
from googleapiclient import discovery

from counter_speech_bot.rate_limiter import RateLimiter


PERSPECTIVE_API_KEY = ''  # copy and paste in the key for now


class CounterSpeechBot:

    def __init__(self, args):
        self.tweetset_path = args.tweetset_path
        self.attributes = args.attributes
        self.service = discovery.build('commentanalyzer', 'v1alpha1', developerKey=PERSPECTIVE_API_KEY)
        self.errors = defaultdict(lambda: 0)

    def get_toxicity(self, request):
        try:
            return self.service.comments().analyze(body=request).execute()
        except googleapiclient.errors.HttpError as e:
            # weirdly the error_details aren't set on the error object until after this is called
            e._get_reason()
            error_type = e.error_details[0]['errorType']
            self.errors[error_type] += 1
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

    def main(self):
        print(f"Loading tweets from {self.tweetset_path}")
        with open(self.tweetset_path, 'r') as f:
            tweetset = (line.strip() for line in f.readlines())

        rate_limiter = RateLimiter(max_calls_per_second=1)
        for tweet in tweetset:
            rate_limiter.wait()
            print(f"Tweet: {tweet}")
            request = self.build_request(tweet)
            response = self.get_toxicity(request)
            if response:
                for attribute in self.attributes:
                    print(f"- {attribute}: {response['attributeScores'][attribute]['summaryScore']['value']}")

        print('Done!')
        print(f"Total errors encountered: {sum(self.errors.values())}")
        for error_type, count in self.errors.items():
            print(f"- {len(count)} {error_type} errors")


if __name__ == '__main__':
    """
    Example command:
    python -m main --tweetset-path tmp/tweetsets.csv --atributes TOXICITY IDENTITY_ATTACK INSULT
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--tweetset-path', required=True, help='Path to the file where the tweetset is stored')
    parser.add_argument(
        '--attributes',
        nargs='+',
        default=['TOXICITY', 'IDENTITY_ATTACK'],
        help='List of attributes to analyze for each tweet. See https://support.perspectiveapi.com/s/about-the-api-attributes-and-languages',
    )
    args = parser.parse_args()
    CounterSpeechBot(args).main()
