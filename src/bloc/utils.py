"""
Sample utility functions
"""

def check_status(resp, statuses):
    """
    Raise Exception when response code is not one of statuses
    """
    if resp.code not in statuses:
        raise Exception('unexpected resp code: {}'.format(resp.code))
    return resp
