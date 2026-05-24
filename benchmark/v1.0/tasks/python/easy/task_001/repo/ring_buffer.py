"""
ring_buffer.py — A fixed-capacity circular (ring) buffer.

Supports O(1) enqueue and dequeue, constant memory usage, and
non-destructive inspection of the oldest element via peek().
"""


class RingBufferFullError(Exception):
    """Raised when enqueue() is called on a full buffer."""


class RingBufferEmptyError(Exception):
    """Raised when dequeue() or peek() is called on an empty buffer."""


class RingBuffer:
    """Fixed-capacity FIFO circular buffer.

    Elements are stored in a pre-allocated list.  ``head`` points to the
    slot that will be written next; ``tail`` points to the oldest element
    currently in the buffer.

    Args:
        capacity: Maximum number of elements the buffer can hold (must be > 0).
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._capacity = capacity
        self._data: list = [None] * capacity
        self._head = 0   # next write position
        self._tail = 0   # oldest element position
        self._size = 0

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def enqueue(self, value) -> None:
        """Add *value* to the back of the buffer.

        Raises:
            RingBufferFullError: if the buffer is already at capacity.
        """
        if self._size == self._capacity:
            raise RingBufferFullError("buffer is full")
        self._data[self._head] = value
        self._head = (self._head + 1) % self._capacity
        self._size += 1

    def dequeue(self):
        """Remove and return the oldest element from the buffer.

        Raises:
            RingBufferEmptyError: if the buffer is empty.
        """
        if self._size == 0:
            raise RingBufferEmptyError("buffer is empty")
        value = self._data[self._tail]
        self._tail = (self._tail + 1) % self._capacity
        self._size -= 1
        return value

    def peek(self):
        """Return the oldest element without removing it.

        Raises:
            RingBufferEmptyError: if the buffer is empty.
        """
        if self._size == 0:
            raise RingBufferEmptyError("buffer is empty")
        return self._data[self._head]

    # ------------------------------------------------------------------
    # Informational
    # ------------------------------------------------------------------

    def is_empty(self) -> bool:
        """Return True if the buffer contains no elements."""
        return self._size == 0

    def is_full(self) -> bool:
        """Return True if the buffer is at capacity."""
        return self._size == self._capacity

    def __len__(self) -> int:
        """Return the number of elements currently in the buffer."""
        return self._size

    def __repr__(self) -> str:  # pragma: no cover
        items = []
        for i in range(self._size):
            items.append(repr(self._data[(self._tail + i) % self._capacity]))
        return f"RingBuffer(capacity={self._capacity}, items=[{', '.join(items)}])"
