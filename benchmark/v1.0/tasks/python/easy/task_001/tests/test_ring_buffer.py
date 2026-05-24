"""
Example test suite for RingBuffer — visible to the agent as a feedback signal.

These tests exercise the public API described in prompt.md.  They are *correct*
(the expected values are right); any failure reflects a bug in the implementation.

Run with:
    pytest tests/
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "repo"))

import pytest
from ring_buffer import RingBuffer, RingBufferFullError, RingBufferEmptyError


# ---------------------------------------------------------------------------
# Basic enqueue / dequeue / len
# ---------------------------------------------------------------------------

def test_enqueue_and_dequeue_single_element():
    buf = RingBuffer(4)
    buf.enqueue(42)
    assert len(buf) == 1
    assert buf.dequeue() == 42
    assert len(buf) == 0


def test_fifo_order_preserved():
    buf = RingBuffer(4)
    for v in [10, 20, 30]:
        buf.enqueue(v)
    assert buf.dequeue() == 10
    assert buf.dequeue() == 20
    assert buf.dequeue() == 30


# ---------------------------------------------------------------------------
# peek — the buggy method
# ---------------------------------------------------------------------------

def test_peek_returns_oldest_element_no_dequeue():
    """peek() must return the same element as the next dequeue() call."""
    buf = RingBuffer(4)
    buf.enqueue("a")
    buf.enqueue("b")
    buf.enqueue("c")

    assert buf.peek() == "a"          # oldest element
    assert len(buf) == 3              # peek must not consume the element
    assert buf.dequeue() == "a"       # dequeue must agree with peek


def test_peek_after_partial_dequeue():
    """
    After dequeueing some elements the write pointer has advanced past the
    original start.  peek() must still point at the current oldest element,
    not at the write position.
    """
    buf = RingBuffer(3)
    buf.enqueue(1)
    buf.enqueue(2)
    buf.enqueue(3)
    buf.dequeue()           # remove 1; oldest is now 2
    buf.dequeue()           # remove 2; oldest is now 3

    # At this point _tail == 2, _head == 0 (wrapped around in a cap-3 buffer).
    # peek() must return 3 (the value at _tail), not whatever is at _head.
    assert buf.peek() == 3
    assert buf.dequeue() == 3
