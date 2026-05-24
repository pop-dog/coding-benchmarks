# ring_buffer — Fixed-Capacity Circular Buffer

`ring_buffer.py` provides a generic, fixed-capacity FIFO circular buffer
implemented in pure Python.

## Features

- **O(1) enqueue and dequeue** — all operations are constant time.
- **Constant memory** — the internal storage is pre-allocated at construction;
  no allocations occur during normal operation.
- **Non-destructive peek** — inspect the oldest element without removing it.
- **Clear error semantics** — raises `RingBufferFullError` on overflow and
  `RingBufferEmptyError` on underflow.

## Quick start

```python
from ring_buffer import RingBuffer, RingBufferFullError, RingBufferEmptyError

buf = RingBuffer(capacity=4)

buf.enqueue("a")
buf.enqueue("b")
buf.enqueue("c")

print(buf.peek())    # "a"  — oldest element, not removed
print(len(buf))      # 3

print(buf.dequeue()) # "a"
print(buf.dequeue()) # "b"
print(buf.peek())    # "c"
```

## API

| Method | Description |
|---|---|
| `enqueue(value)` | Add an element to the back of the buffer |
| `dequeue()` | Remove and return the oldest element |
| `peek()` | Return the oldest element without removing it |
| `is_empty()` | `True` if the buffer holds no elements |
| `is_full()` | `True` if the buffer is at capacity |
| `len(buf)` | Number of elements currently stored |
