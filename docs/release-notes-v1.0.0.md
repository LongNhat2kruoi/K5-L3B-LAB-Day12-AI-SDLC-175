# Quán Ăn Chợ Nổi v1.0.0

## Có gì mới

- Một ngày liên tục: Lặn & Hái → Mở Quán → đóng ca.
- Kho cá thể v1.2 với độ tươi, hàng ươn, giữ chỗ theo id và giá theo độ tươi.
- Contract root v1.3: benchmark 30 giây, soak nhiều ngày và leaderboard top 10.
- Client Pyxel/web có cảnh báo chữ/icon và chế độ tương phản cao (`C`).

## Chạy nhanh

```bash
python3 -m chonoi.live --mode day
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.benchmark --seed 42 --duration 30 --out bench.json
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
```

## Giới hạn đã biết

- `quetoi.mp3` cần xác nhận nguồn/license trước khi phát hành công khai.
- Soak headless dùng bot rỗng để kiểm tra tiến trình và tính tất định; chưa đại diện cho chiến thuật kiếm tiền tối ưu.
- Git tag `phase-4` và GitHub Release `v1.0.0` phải được tạo cùng commit bàn giao trên `main` sau khi regression xanh.
