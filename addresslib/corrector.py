# coding:utf-8
"""
Spelling corrector library, used to correct common typos in domains like
gmal.com instead of gmail.com.

The spelling corrector uses difflib which in turn uses the
Ratcliff-Obershelp algorithm [1] to compute the similarity of two strings.
This is a very fast an accurate algorithm for domain spelling correction.

The (only) public method this module has is suggest(word), which given
a domain, suggests an alternative or returns the original domain
if no suggestion exists.

[1] http://xlinux.nist.gov/dads/HTML/ratcliffObershelp.html
"""

import difflib


def suggest(word, cutoff=0.77):
    """
    Given a domain and a cutoff heuristic, suggest an alternative or return the
    original domain if no suggestion exists.
    """
    if word in LOOKUP_TABLE:
        return LOOKUP_TABLE[word]

    guess = difflib.get_close_matches(word, MOST_COMMON_DOMAINS, n=1, cutoff=cutoff)
    if guess and len(guess) > 0:
        return guess[0]
    return word


MOST_COMMON_DOMAINS = [
    # mailgun :)
    'mailgun.net',
    # big esps
    'yahoo.com',
    'yahoo.ca',
    'yahoo.co.jp',
    'yahoo.co.uk',
    'ymail.com',
    'hotmail.com',
    'hotmail.ca',
    'hotmail.co.uk',
    'windowslive.com',
    'live.com',
    'outlook.com',
    'msn.com',
    'gmail.com',
    'googlemail.com',
    'aol.com',
    'aim.com',
    'icloud.com',
    'me.com',
    'mac.com',
    'facebook.com',
    # big isps
    'comcast.net',
    'sbcglobal.net',
    'bellsouth.net',
    'verizon.net',
    'earthlink.net',
    'cox.net',
    'charter.net',
    'shaw.ca',
    'bell.net'
]

# domains that the corrector doesn't fix that we should fix
LOOKUP_TABLE = {
    'yahoo':       'yahoo.com',
    'gmail':       'gmail.com',
    'hotmail':     'hotmail.com',
    'live':        'live.com',
    'outlook':     'outlook.com',
    'msn':         'msn.com',
    'googlemail':  'googlemail.com',
    'aol':         'aol.com',
    'aim':         'aim.com',
    'icloud':      'icloud.com',
    'me':          'me.com',
    'mac':         'mac.com',
    'facebook':    'facebook.com',
    'comcast':     'comcast.net',
    'sbcglobal':   'sbcglobal.net',
    'bellsouth':   'bellsouth.net',
    'verizon':     'verizon.net',
    'earthlink':   'earthlink.net',
    'cox':         'cox.net',
    'charter':     'charter.net',
    'shaw':        'shaw.ca',
    'bell':        'bell.net'
}
