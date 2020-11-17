from googleapiclient import discovery
import os

PERSPECTIVE_API_KEY=os.environ['PERSPECTIVE_API_KEY']

# Generates API client object dynamically based on service name and version.
service = discovery.build('commentanalyzer', 'v1alpha1', developerKey=PERSPECTIVE_API_KEY)

analyze_request = {
  'comment': { 'text': 'friendly greetings from python' },
  'requestedAttributes': {'TOXICITY': {}}
}

response = service.comments().analyze(body=analyze_request).execute()

import json
print(json.dumps(response, indent=2))