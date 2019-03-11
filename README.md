# TriviaGame
Cloud Computing Final Project:

1) Beanstalk for presentation
2) S3 Bucket to store db info:
    - One for raw info, based on history
    - One for sorted list of scores maybe
        (Needs sorting algorithm and would overwrite the user's prior score if their score is higher)

3) DynamoDB to present data from S3 bucket with score as PK?
    (PK could be e-mail address as it should be 'unique', and it would return their prior high score)
    
4) API Call to establish Trivia game - Done

5) Notifications system to notify user if new 'high score' placed

// 6) CloudFront to dl current score list of players ?????
7) Account creation that stores username/email used for notification and grabbing their score within the list of high scores
