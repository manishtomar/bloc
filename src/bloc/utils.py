"""
Sample utility functions
"""


def check_status(resp, statuses):
    """
    Raise Exception when response code is not one of statuses.
    This function is not required once https://github.com/twisted/treq/issues/62 is fixed
    """
    if resp.code not in statuses:
        raise Exception('unexpected resp code: {}'.format(resp.code))
    return resp
