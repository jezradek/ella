from ella.utils.settings import Settings

ACTIVITY_NOT_YET_ACTIVE = 0
ACTIVITY_ACTIVE = 1
ACTIVITY_CLOSED = 2

IP_VOTE_TRESHOLD = 10 * 60

POLL_COOKIE_NAME = 'polls_voted'
POLL_JUST_VOTED_COOKIE_NAME = 'polls_just_voted_voted'
POLL_NO_CHOICE_COOKIE_NAME = 'polls_no_choice'
POLL_MAX_COOKIE_LENGTH = 20
POLL_MAX_COOKIE_AGE = 604800

SURVEY_COOKIE_NAME = 'surveys_voted'
SURVEY_JUST_VOTED_COOKIE_NAME = 'surveys_just_voted_voted'
SURVEY_NO_CHOICE_COOKIE_NAME = 'surveys_no_choice'
SURVEY_MAX_COOKIE_LENGTH = 20
SURVEY_MAX_COOKIE_AGE = 604800

USER_NOT_YET_VOTED = 0
USER_JUST_VOTED = 1
USER_ALLREADY_VOTED = 2
USER_NO_CHOICE = 3


polls_settings = Settings('ella.polls.conf', 'POLLS')