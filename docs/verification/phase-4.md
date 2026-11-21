# Ma trận truy vết Phase 4 (TICKET-04)

## Kết quả trên commit bàn giao

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 Contract v1.3 khai `bench_cmd`, `soak_cmd` và extension leaderboard | `game.contract.json`, `python -m chonoi.contract` qua bộ test | [game.contract.json](../../game.contract.json) | Đạt |
| AC-P4-02 Benchmark nhận seed/duration/out và ghi đủ 5 trường | `python -m chonoi.benchmark --seed 42 --duration 30 --out bench.json` | [bench.json](../proof/phase-4/bench.json) | Đạt: 60 FPS, 1% low 60, load dưới 10 s |
| AC-P4-03 Soak 10 ngày không crash | `python -m chonoi.soak --seed 7 --days 10 --out soak.json` | [soak.json](../proof/phase-4/soak.json) | Đạt: `days_completed=10`, `crashes=0` |
| AC-P4-04 Cảnh báo thủy quái, oxy, khách sắp giận và chế độ tương phản cao | Client web: các cảnh báo có chữ/icon; phím `C` hoặc nút tương phản cao | [web client](../../chonoi/web/index.html), [Pyxel client](../../play/main.py) | Đạt ở UI; headless không bật phần sáng tạo |
| AC-P4-05 Leaderboard top 10 bền vững, export ổn định | Chạy day chuẩn 5 ngày với `--leaderboard --player-name`, sau đó `--export-leaderboard` | [leaderboard.py](../../chonoi/leaderboard.py) | Đạt; chỉ ghi khi đủ 5 ngày, không ghi soak |
| AC-P4-06 Regression P1–P3 | `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` | `tests/` và log CI | Đang cập nhật fixture legacy cho contract v1.3; phải xanh trước tag |

## Lệnh bàn giao

```text
python3 -m chonoi.live --mode day
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.benchmark --seed 42 --duration 30 --out bench.json
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```

Các artifact JSON trong thư mục này được sinh từ mã tại commit bàn giao; `duration_s` chỉ là số đo máy chạy và không dùng khi so tính lặp gameplay.
