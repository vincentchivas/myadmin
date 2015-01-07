# coder yfhe
import datetime
DEFAULT_SOURCE = 'ofw'
ALL_FLAG = 'all_condition'
OTHER = 'other_condition'
OPERATORS = ['00', '01', '02', '03']
now = datetime.datetime.utcnow
ALL_WEIGHT = 1
MATCH_WEIGHT = 100

BASE_PARAS = [
    'pn&option',
    'chn&option',
    'vn&option&1&int',
    'op&option',
    'lc&option',
    'lo&option',
    'mt&option&0&int',
]

SHARE_PARAS = {
    'pn&BeNone',
    'lc&BeNone',
    'appvc&option&0&int',
    'chn&option&ofw&str',
    'no&BeNone',
}

DESKTOP_PARAS = {
    'pn&BeNone',
    'lc&BeNone',
    'appvc&option&0&int',
    'chn&option&ofw&str',
    'no&option&other_condition&str',
}

PRESET_PARAS = {
    'os&option&',
    'osv&BeNone',
    'model&BeNone',
    'nt&BeNone',
    'no&BeNone',
    'lc&BeNone',
    'pn&BeNone',
    'appvc&option&0&int',
    'res&BeNone',
    'did&BeNone',
    'appvn&BeNone',
    'cpu&BeNone',
    'chn&option&ofw&str',
    'nd&option&0&bool',
}

RULE_ORIGINIZE = {
    'pn': ['{"_rule.packages":"%s"}', 1],
    'appvc': ['{"_rule.min_version":{"$lte":%s},"_rule.max_version":{"$gte":%s}}', 2],
    'no': ['{"_rule.operators":{"$in":["%s",ALL_FLAG]}}', 1],
    'chn': ['{"_rule.sources.include":{"$in":["%s", "ofw", ALL_FLAG]},"_rule.sources.exclude":{"$ne":"%s"}}', 2],
    'lc': ['{"_rule.locales.include":{"$in":["%s",ALL_FLAG]},"_rule.locales.exclude":{"$ne":"%s"}}', 2],
    'lo': ['{"_rule.locations.include":{"$in":["%s",ALL_FLAG]},"_rule.locations.exclude":{"$ne":"%s"}}', 2],
    'time_valid': ['{"_rule.start_time": {"$lte": now()}, "_rule.end_time": {"$gte": now()}}', 0],
    'mt': ['{"mt":{"$gt":%d}}', 1]
}

SKIN_ORIGINIZE = {
    'cv': ["{'c_version': %d}", 1],
    'type': ["{'theme_type':'%s'}", 1],
    'promote': ["{'promote': %s}", 1],
    'uid': ["{'uid': '%s'}", 1],
    'id': ["{'id':%d}", 1],
}

OTHER_ORIGINIZE = {
    'mt': ['{"last_modified":{"$gt":%d}}', 1],
    #'lc': ['{"_rule.locales:', 2],
}
