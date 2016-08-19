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


# Taken from https://github.com/rackerlabs/otter/blob/master/otter/util/deferredutils.py
# but ideally should be in twisted http://tm.tl/5786

class TimedOutError(Exception):
    """
    Exception that gets raised by timeout_deferred
    """
    def __init__(self, timeout, deferred_description):
        super(TimedOutError, self).__init__(
            "{desc} timed out after {timeout} seconds.".format(
                desc=deferred_description, timeout=timeout))


def timeout_deferred(deferred, timeout, clock, deferred_description=None):
    """
    Time out a deferred - schedule for it to be canceling it after ``timeout``
    seconds from now, as per the clock.

    If it gets timed out, it errbacks with a :class:`TimedOutError`, unless a
    cancelable function is passed to the ``Deferred``'s initialization and it
    callbacks or errbacks with something else when cancelled.
    (see the documentation for :class:`twisted.internet.defer.Deferred`)
    for more details.

    :param Deferred deferred: Which deferred to time out (cancel)
    :param int timeout: How long before timing out the deferred (in seconds)
    :param str deferred_description: A description of the Deferred or the
        Deferred's purpose - if not provided, defaults to the ``repr`` of the
        Deferred.  To be passed to :class:`TimedOutError` for a pretty
        Exception string.
    :param IReactorTime clock: Clock to be used to schedule the timeout -
        used for testing.

    :return: ``None``

    based on:  https://twistedmatrix.com/trac/ticket/990
    """
    timed_out = [False]

    def time_it_out():
        timed_out[0] = True
        deferred.cancel()

    delayed_call = clock.callLater(timeout, time_it_out)

    def convert_cancelled(f):
        # if the failure is CancelledError, and we timed it out, convert it
        # to a TimedOutError.  Otherwise, propagate it.
        if timed_out[0]:
            f.trap(defer.CancelledError)
            raise TimedOutError(timeout, deferred_description)
        return f

    deferred.addErrback(convert_cancelled)

    def cancel_timeout(result):
        # stop the pending call to cancel the deferred if it's been fired
        if delayed_call.active():
            delayed_call.cancel()
        return result

    deferred.addBoth(cancel_timeout)
