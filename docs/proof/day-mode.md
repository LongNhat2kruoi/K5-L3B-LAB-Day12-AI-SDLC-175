# Bằng chứng extension `day`

## Phạm vi

Một session bắt đầu ở `gather`, giữ inventory trong giỏ, rồi tự dựng `quan` khi có `gather_end`. Event `phase_changed` đánh dấu chuyển phase; snapshot giữ `mode: "day"`.

## Kiểm chứng

```text
PYTHONPATH=tests;. python -m unittest discover -s tests -v
```

Kết quả sau khi đồng bộ `origin/main`: **180 tests, OK**.

Test liên quan: `tests/test_day_mode.py`, `tests/test_live.py` và `tests/test_smoke_p1.py`.

Smoke CLI:

```text
python -m chonoi.headless --mode day --seed 1 --ticks 0 --out day-zero.jsonl
```

Snapshot đầu ra có `mode: "day"`, `phase: "gather"`, `phase_tick: 0`; khi gather kết thúc, phase chuyển sang `quan` và stock lấy từ inventory gather.
