# Task: Fix the ring buffer implementation

## Background

The `ring_buffer.py` module implements a fixed-capacity circular (ring) buffer — a
common data structure used in streaming, producer/consumer pipelines, and embedded
systems.  The buffer is FIFO: the first element enqueued is the first one dequeued.

The module exposes a `RingBuffer` class with the following public interface:

| Method | Expected behaviour |
|---|---|
| `enqueue(value)` | Add `value` to the back of the buffer; raise `RingBufferFullError` if full |
| `dequeue()` | Remove and return the oldest element; raise `RingBufferEmptyError` if empty |
| `peek()` | Return the oldest element **without** removing it; raise `RingBufferEmptyError` if empty |
| `is_empty()` | Return `True` if the buffer is empty |
| `is_full()` | Return `True` if the buffer is at capacity |
| `len(buf)` | Return the number of elements currently in the buffer |

## What is going wrong

The test suite is reporting unexpected values from `peek()`.  Specifically, after
enqueueing several items and then dequeueing some of them, `peek()` returns a value
that does not match what `dequeue()` subsequently returns.  The two methods should
always agree on which element is "oldest" — but right now they don't.

The bug is subtle: it only surfaces once the buffer's internal write pointer has
advanced past the read pointer (i.e., after elements have been both enqueued and
dequeued, causing the internal ring to wrap or shift).  A fresh buffer with items
enqueued but none dequeued may appear to work correctly in simple tests.

## Your task

1. Read `ring_buffer.py` and identify the defect in the implementation.
2. Fix the defect so that `peek()` reliably returns the same element that the next
   call to `dequeue()` would return.
3. Do **not** change the public interface or the existing test files.

The fix should require changing **one line** of source code in `ring_buffer.py`.

## Constraints

- Only modify `repo/ring_buffer.py`.
- Do not modify any test files.
- After your fix, all tests in `tests/` must pass.
