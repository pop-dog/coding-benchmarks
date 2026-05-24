"""
Hidden evaluation suite for RingBuffer — NOT exposed to the agent.

Every test here must PASS after the correct fix is applied to ring_buffer.py
and must FAIL against the unmodified (buggy) repo.  The suite is more thorough
than the example tests, covering edge cases and wrap-around scenarios that
make the off-by-one defect in peek() unambiguously detectable.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "repo"))

import pytest
from ring_buffer import RingBuffer, RingBufferFullError, RingBufferEmptyError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def drain(buf):
    """Return all elements from buf via dequeue(), leaving it empty."""
    result = []
    while not buf.is_empty():
        result.append(buf.dequeue())
    return result


# ---------------------------------------------------------------------------
# peek correctness (the core defect)
# ---------------------------------------------------------------------------

class TestPeek:
    def test_peek_fresh_buffer_single_item(self):
        buf = RingBuffer(5)
        buf.enqueue("x")
        assert buf.peek() == "x"

    def test_peek_does_not_remove_element(self):
        buf = RingBuffer(5)
        buf.enqueue(99)
        _ = buf.peek()
        assert len(buf) == 1
        assert buf.dequeue() == 99

    def test_peek_agrees_with_dequeue_after_one_removal(self):
        buf = RingBuffer(4)
        buf.enqueue("a")
        buf.enqueue("b")
        buf.enqueue("c")
        buf.dequeue()                  # consume "a"; oldest is now "b"
        assert buf.peek() == "b"
        assert buf.dequeue() == "b"

    def test_peek_agrees_with_dequeue_after_two_removals(self):
        buf = RingBuffer(4)
        for v in ["a", "b", "c", "d"]:
            buf.enqueue(v)
        buf.dequeue()                  # "a"
        buf.dequeue()                  # "b"
        assert buf.peek() == "c"
        assert buf.dequeue() == "c"

    def test_peek_after_wrap_around(self):
        """
        Fill a capacity-3 buffer, drain it fully, then refill.
        Both _head and _tail will have wrapped; peek must use _tail.
        """
        buf = RingBuffer(3)
        buf.enqueue(1)
        buf.enqueue(2)
        buf.enqueue(3)
        drain(buf)                     # _head == _tail == 0, _size == 0

        buf.enqueue(10)
        buf.enqueue(20)

        assert buf.peek() == 10
        assert buf.dequeue() == 10
        assert buf.peek() == 20
        assert buf.dequeue() == 20

    def test_peek_interleaved_enqueue_dequeue(self):
        """Interleave enqueues and dequeues so pointers cross mid-array."""
        buf = RingBuffer(4)
        buf.enqueue("p")
        buf.enqueue("q")
        buf.dequeue()                  # remove "p"; _tail=1, _head=2
        buf.enqueue("r")               # _head=3
        buf.enqueue("s")               # _head=0 (wrapped)

        # Oldest is "q" (at _tail=1), _head is now 0.
        assert buf.peek() == "q"
        assert buf.dequeue() == "q"

        assert buf.peek() == "r"
        assert buf.dequeue() == "r"

        assert buf.peek() == "s"
        assert buf.dequeue() == "s"

    def test_peek_repeated_calls_return_same_value(self):
        buf = RingBuffer(3)
        buf.enqueue(7)
        buf.enqueue(8)
        # Call peek multiple times — result must be stable.
        for _ in range(5):
            assert buf.peek() == 7

    def test_peek_empty_raises(self):
        buf = RingBuffer(2)
        with pytest.raises(RingBufferEmptyError):
            buf.peek()

    def test_peek_after_full_cycle(self):
        """
        Enqueue capacity items, dequeue all, re-enqueue different items.
        Peek must track the new oldest element correctly.
        """
        cap = 5
        buf = RingBuffer(cap)
        for i in range(cap):
            buf.enqueue(i * 10)
        drain(buf)
        for i in range(cap):
            buf.enqueue(i * 100)

        for expected in [0, 100, 200, 300, 400]:
            assert buf.peek() == expected
            assert buf.dequeue() == expected


# ---------------------------------------------------------------------------
# enqueue / dequeue correctness (regression guard — must not be broken by fix)
# ---------------------------------------------------------------------------

class TestEnqueueDequeue:
    def test_fifo_order(self):
        buf = RingBuffer(6)
        items = list(range(6))
        for v in items:
            buf.enqueue(v)
        assert drain(buf) == items

    def test_enqueue_full_raises(self):
        buf = RingBuffer(2)
        buf.enqueue(1)
        buf.enqueue(2)
        with pytest.raises(RingBufferFullError):
            buf.enqueue(3)

    def test_dequeue_empty_raises(self):
        buf = RingBuffer(2)
        with pytest.raises(RingBufferEmptyError):
            buf.dequeue()

    def test_reuse_after_drain(self):
        buf = RingBuffer(3)
        buf.enqueue("x")
        drain(buf)
        buf.enqueue("y")
        assert buf.dequeue() == "y"

    def test_interleaved_fill_and_drain(self):
        buf = RingBuffer(3)
        buf.enqueue(1)
        buf.enqueue(2)
        assert buf.dequeue() == 1
        buf.enqueue(3)
        buf.enqueue(4)
        assert drain(buf) == [2, 3, 4]


# ---------------------------------------------------------------------------
# Capacity / size reporting
# ---------------------------------------------------------------------------

class TestSizeAndCapacity:
    def test_is_empty_on_new_buffer(self):
        assert RingBuffer(3).is_empty()

    def test_is_full_when_at_capacity(self):
        buf = RingBuffer(2)
        buf.enqueue(1)
        buf.enqueue(2)
        assert buf.is_full()

    def test_len_tracks_enqueue_and_dequeue(self):
        buf = RingBuffer(4)
        for i in range(4):
            buf.enqueue(i)
            assert len(buf) == i + 1
        for i in range(4, 0, -1):
            buf.dequeue()
            assert len(buf) == i - 1

    def test_invalid_capacity_raises(self):
        with pytest.raises(ValueError):
            RingBuffer(0)
        with pytest.raises(ValueError):
            RingBuffer(-1)
