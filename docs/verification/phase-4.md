# Ma trận truy vết Phase 4 (TICKET-04)

## Kết quả trên commit bàn giao

| AC | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| AC-P4-01 Contract v1.3 khai `bench_cmd`, `soak_cmd` và extension leaderboard | `game.contract.json`, `python -m chonoi.contract` qua bộ test | [game.contract.json](../../game.contract.json) | Đạt |
| AC-P4-02 Benchmark có render: cảnh sáng Ngày 1, cửa sổ 1280×720 (Pyxel 320×180 ×4), làm nóng 3 s, đo 30 s, ghi đủ 5 trường | `python3 -m chonoi.benchmark --seed 42 --duration 30 --out bench.json` (cần `pip install pyxel`); công thức kiểm bằng `tests/test_benchmark.py` | [bench.json](../proof/phase-4/bench.json) | Đạt phần lệnh và cấu trúc. Số đo thật trên máy Windows của quangpham: avg 59.47 FPS, 1% low 26.57 FPS, load 1.30 s (lần chạy trước: 59.73 / 35.76 / 0.81 s). avg bị chặn ở 60 vì client chạy `fps=60`; 1% low dao động quanh mốc 30. Cảnh chưa có cá bơi và Cá Sấu vì sim chưa làm, không giả lập. |
| AC-P4-03 Soak 10 ngày không crash | `python -m chonoi.soak --seed 7 --days 10 --out soak.json` | [soak.json](../proof/phase-4/soak.json) | Đạt: `days_completed=10`, `crashes=0` |
| AC-P4-04 Cảnh báo thủy quái, oxy, khách sắp giận và chế độ tương phản cao | Client web: các cảnh báo có chữ/icon; phím `C` hoặc nút tương phản cao | [web client](../../chonoi/web/index.html), [Pyxel client](../../play/main.py) | Đạt ở UI; headless không bật phần sáng tạo |
| AC-P4-05 Leaderboard top 10 bền vững, export ổn định | Chạy day chuẩn 5 ngày với `--leaderboard --player-name`, sau đó `--export-leaderboard` | [leaderboard.py](../../chonoi/leaderboard.py) | Đạt; chỉ ghi khi đủ 5 ngày, không ghi soak |
| AC-P4-06 Regression P1–P3 | `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v` | [regression.txt](../proof/phase-4/regression.txt) | Đạt: 190 test OK (2 test cửa sổ bỏ qua khi không đặt `BENCH_GUI=1`). Fixture đã chuyển sang kho cá thể v1.2, bỏ cờ tương thích cũ (commit `7969a48`…`246dde9`) |

## Lệnh bàn giao

```text
python3 -m chonoi.live --mode day
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.benchmark --seed 42 --duration 30 --out bench.json
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```

Các artifact JSON trong thư mục này được sinh từ mã tại commit bàn giao; `duration_s` chỉ là số đo máy chạy và không dùng khi so tính lặp gameplay.
