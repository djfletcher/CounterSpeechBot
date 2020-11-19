# CounterSpeechBot
This project prototypes a Twitter bot that counters hate speech. Currently it supports two modes: stream processing and batch processing. In the stream processing mode, the script samples roughly 1% of publicly available tweets in real-time. In the batch processing mode, the script loads a user-provided dataset into memory for processing. In both modes the script scores tweets according to toxicity attributes from the [Perspective API](https://www.perspectiveapi.com/), and any tweets that meet the user-configured thresholds are persisted to a local file.

The bot does not post any replies yet. Currently, it logs potential replies for review by humans.

## Context

Social media regulation and internet policy in the US are very much a work in progress. One of the most hotly debated topics is censorship on social media, because social media companies have struggled to maintain healthy civic discourses on their platforms while also granting a measure of "free speech" rights to their users. One possible resolution to this issue might be found in [counter-speech](https://en.wikipedia.org/wiki/Counterspeech): studies have shown that counter-speech may be an effective alternative to censorship at reducing the amount of hate speech on social media:
> In one of the only studies that explicitly detects naturally occurring counter-speech on social media, Mathew et al. [1](#citations) find that counter-speech comments receive much more likes and engagement than other comments and may prompt producers of hate speech to apologize or change their behavior. [2](#citations)

The idea for this project was conceived as a result of learning of that study and then reading [this Forbes opinion article](https://www.forbes.com/sites/kalevleetaru/2017/02/04/fighting-social-media-hate-speech-with-ai-powered-bots/?sh=2386d90527b1), which proposed deploying AI bots en masse to fight online hate speech. I find the idea really intriguing, especially in an era where social media policy and the efficacy of online censorship is hotly debated.

## Goal
Prototype a Twitter bot that can identify tweets containing hate speech and respond to them with counter-speech. There are open source hate speech identification models and APIs that we can use, so we don't have to try to create one from scratch (though there are open source data sets for this if somebody did want to try to train a model). We can have our bot listen on Twitter's open API and if a tweet is published that the bot thinks might be hate speech, the bot can automatically respond to the offending tweet with counter-speech. At first, the counter-speech could be very simple or general like "This comment could be considered an identity attack on a group of people." Later, we could try to develop a more intelligent NLP model that posts more targeted and intelligent replies.

The goal is not to start Twitter fights. The goal is to prototype a counter-speech bot that challenges hate speech.

## MVP
MVP looks like a script or a service that, given a tweet or a stream of tweets, identifies ones containing hate speech with reasonable accuracy and logs a potential response to each.

## Setup Instructions
1. `git clone https://github.com/djfletcher/CounterSpeechBot.git`
2. `cd CounterSpeechBot`
3. `make requirements`
5. `source venv/bin/activate`
6. Create an `.api_keys` file containing the necessary keys. You will need a [Perspective API key](https://support.perspectiveapi.com/s/docs-get-started) and a [Twitter API key](https://developer.twitter.com/en/docs/twitter-api/getting-started/guide).
Your `.api_keys` file should be in the format:
```
TWITTER_BEARER_TOKEN=<your key here>
PERSPECTIVE_API_KEY=<your key here>
```
  Make sure you keep these keys secret:
```
chmod 600 .api_keys  # restrict permissions so that only you can read the file
```
7. `python -m counter_speech_bot.realtime_bot -h` or `python -m counter_speech_bot.tweetset_bot -h`


## Example
```
(venv) CounterSpeechBot (main) $ python -m counter_speech_bot.realtime_bot -h
usage: realtime_bot.py [-h] [--total-tweet-limit TOTAL_TWEET_LIMIT]
                       [--toxic-tweet-limit TOXIC_TWEET_LIMIT]
                       [--attributes ATTRIBUTES [ATTRIBUTES ...]]
                       [--toxicity-threshold TOXICITY_THRESHOLD]
                       [--identity-attack-threshold IDENTITY_ATTACK_THRESHOLD]
                       [--insult-threshold INSULT_THRESHOLD]
                       [--include-non-english] [--tracking-file TRACKING_FILE]
                       [--append-to-existing-file]
Randomly samples roughly 1% of publicly available tweets in real-time and
scores them according to toxicity attributes from the Perspective API
optional arguments:
  -h, --help            show this help message and exit
  --total-tweet-limit TOTAL_TWEET_LIMIT
                        Quit when the specified number of tweets have been
                        processed.
  --toxic-tweet-limit TOXIC_TWEET_LIMIT
                        Quit when the specified number of toxic tweets have
                        been processed.
  --attributes ATTRIBUTES [ATTRIBUTES ...]
                        Space-separate list of attributes to analyze for each
                        tweet. See https://support.perspectiveapi.com/s/about-
                        the-api-attributes-and-languages for available
                        attributes | default: TOXICITY IDENTITY_ATTACK
  --toxicity-threshold TOXICITY_THRESHOLD
                        Only process tweets whose toxicity is scored above
                        this threshold. Must be a decimal between 0 and 1. |
                        Default 0.5
  --identity-attack-threshold IDENTITY_ATTACK_THRESHOLD
                        Only process tweets whose identity attack is scored
                        above this threshold. Must be a decimal between 0 and
                        1. | Default 0.5
  --insult-threshold INSULT_THRESHOLD
                        Only process tweets whose insult is scored above this
                        threshold. Must be a decimal between 0 and 1. |
                        Default 0.5
  --include-non-english
                        If true, includes tweets in all languages. By default,
                        only english tweets are processed | Default: false
  --tracking-file TRACKING_FILE
                        Path to and and name of file to store tweets
                        identified as toxic | Default:
                        toxic_tweets_{start_timestamp}.txt
  --append-to-existing-file
                        If true, appends new toxic tweets to an existing file.
                        Requires --tracking-file | Default: false
```

## TODO
- Concatenate text that spans multiple tweets and send it to analyzer as one text
- Catch when we exceed rate limit and sleep for a period of time
- Handle interrupted connections to Twitter API: https://stackoverflow.com/questions/49064398/requests-exceptions-chunkedencodingerror-connection-broken-incompleteread0

## Resources
 * [Twitter API docs](https://developer.twitter.com/en/docs/twitter-api)
 * [Twitter's Bot Rules](https://help.twitter.com/en/rules-and-policies/twitter-automation)
 * [Twitter's "hateful conduct" policy](https://help.twitter.com/en/rules-and-policies/hateful-conduct-policy)
 * [https://www.perspectiveapi.com/](https://www.perspectiveapi.com/) - an open source ML model for identifying "toxicity". Requires setting up a Google Cloud Project. The model that this API uses under the hood is documented at [https://conversationai.github.io/](https://conversationai.github.io/)

## Citations
1. [https://arxiv.org/abs/1808.04409](https://arxiv.org/abs/1808.04409)
2. [Social Media and Democracy: The State of the Field and Prospects for Reform](https://www.cambridge.org/core/books/social-media-and-democracy/E79E2BBF03C18C3A56A5CC393698F117)

 
