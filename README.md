# CounterSpeechBot
TLDR: Prototype a Twitter bot that counters hate speech

## Context

Social media regulation and internet policy are all over the news these days. One of the most hotly debated topics is censorship on social media, because social media companies have struggled to maintain healthy civic discourses on their platforms while also granting a measure of "free speech" rights to their users. One possible resolution to this thorny issue might be found in [counter-speech](https://en.wikipedia.org/wiki/Counterspeech): studies have shown that counter-speech may be an effective alternative to censorship at reducing the amount of hate speech on social media:
> In one of the only studies that explicitly detects naturally occurring counter-speech on social media, Mathew et al. [1](#citations) find that counter-speech comments receive much more likes and engagement than other comments and may prompt producers of hate speech to apologize or change their behavior. [2](#citations)

The essay I pulled that ^ from also references [this Forbes opinion article](https://www.forbes.com/sites/kalevleetaru/2017/02/04/fighting-social-media-hate-speech-with-ai-powered-bots/?sh=2386d90527b1) that proposed deploying AI bots en masse to fight online hate speech. I find the idea really intriguing, especially in an era where social media policy and the efficacy of online censorship is hotly debated.

## Goal
Let's try to create a Twitter bot that can identify tweets containing hate speech and respond to them with counter-speech. We can see if there are any open source hate speech identification models or apis that we can use, so that we don't have to try to try to create one from scratch (though there are open source data sets for this if somebody did want to try to train a model). We can write a script with some very simple or general counter-speech like "You shouldn't say things like that" or "I find that very offensive." Then we can have our bot listen on Twitter's open API and if a tweet is published that the bot thinks might be hate speech, the bot can automatically respond to the offending tweet with counter-speech.

## MVP
MVP looks like a script or a service that, given a tweet or a stream of tweets, identifies ones containing hate speech with reasonable accuracy and logs a potential response to each. 

## Notes
1. I know this is very ambitious. I'd like to find out how much is feasible in three days.
2. We would want to carefully vet it before having it _actually_ post anything on Twitter. First we can have it log what it _would have_ said in response to tweets that it thinks contain hate speech, and we can see how well it identifies them.
3. The goal is not to start Twitter fights. The goal is to prototype a counter-speech bot that challenges hate speech.

## Setup Instructions
1. `git clone https://github.com/djfletcher/CounterSpeechBot.git`
2. `cd CounterSpeechBot`
3. `make requirements`
5. `source venv/bin/activate`
6. Create an `.api_keys` file containing the necessary keys:
```
vi .api_keys
# paste in keys
:wq
chmod 600 .api_keys  # restricts permissions so only you can read this file
```
Your `.api_keys` file should be in the format:
```
TWITTER_CONSUMER_KEY=<your key here>
TWITTER_CONSUMER_SECRET=<your key here>
TWITTER_BEARER_TOKEN=<your key here>
PERSPECTIVE_API_KEY=<your key here>
```
7. `python -m counter_speech_bot.realtime_bot -h` or `python -m counter_speech_bot.realtime_bot -h`

## Resources
 * [Twitter API docs](https://developer.twitter.com/en/docs/twitter-api)
 * [Twitter's Bot Rules](https://help.twitter.com/en/rules-and-policies/twitter-automation)
 * [Twitter's "hateful conduct" policy](https://help.twitter.com/en/rules-and-policies/hateful-conduct-policy)
 * [https://www.perspectiveapi.com/](https://www.perspectiveapi.com/) - an open source ML model for identifying "toxicity". It looks like you can also query it via API by setting up a Google Cloud Project. The model that this API uses under the hood is documented at [https://conversationai.github.io/](https://conversationai.github.io/)

## Citations
1. [https://arxiv.org/abs/1808.04409](https://arxiv.org/abs/1808.04409)
2. [Social Media and Democracy: The State of the Field and Prospects for Reform](https://www.cambridge.org/core/books/social-media-and-democracy/E79E2BBF03C18C3A56A5CC393698F117)

 
