"""
Tests for :module:`participate
"""

from twisted.trial.unittest import SynchronousTestCase
from twisted.internet.task import Clock

from participate import Partitioner


class ParitionerTests(SynchronousTestCase):
    """
    Tests for :func:`participate.Partitioner`
    """

    def setUp(self):
        self.clock = Clock()
        self.p = Partitioner(self.clock, 10)

    def _check_allocated(self, length):
        self.assertTrue(self.p.allocated)
        self.assertEqual(len(self.p), length)

    def test_add_part_and_settle(self):
        """
        Add a participant and see if it settles after 10 seconds
        """
        self.p.add_participant('p1')
        self.assertFalse(self.p.allocated)
        self.clock.advance(10)
        self._check_allocated(1)
        self.assertEqual(self.p.get_participant_index('p1'), 1)

    def test_add_remove_part_before_timer(self):
        """
        Add participants, move the clock, remove one participant and check
        if it settles after 10 seconds has passed from the last removal
        """
        self.p.add_participant('p1')
        self.p.add_participant('p2')
        self.assertFalse(self.p.allocated)

        self.clock.advance(5)
        self.assertFalse(self.p.allocated)
        self.p.remove_participant('p1')
        self.assertFalse(self.p.allocated)

        # Still not allocated since timer got reset
        self.clock.advance(6)
        self.assertFalse(self.p.allocated)

        self.clock.advance(4)
        self._check_allocated(1)
