import argparse
import json

from googleapiclient import discovery


PERSPECTIVE_API_KEY = ''  # copy and paste in the key for now


class CounterSpeechBot:

    def __init__(self, args):
        self.tweetset_path = args.tweetset_path
        self.attributes = args.attributes
        self.service = discovery.build('commentanalyzer', 'v1alpha1', developerKey=PERSPECTIVE_API_KEY)

    def get_toxicity(self, request):
        return self.service.comments().analyze(body=request).execute()

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
          tweetset = f.read()
          print(f"Analyzing toxicity of {len(tweetset)} tweets")
          for tweet in tweetset:
              print(f"Tweet: {tweet}")
              request = self.build_request(tweet['text'])
              response = self.get_toxicity(request)
              for attribute in self.attributes:
                  print(f"- {attribute}: {response['attributeScores'][attribute]['summaryScore']['value']}")

          print(f"Done!")


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
