# Bằng chứng Gather Resources

Phạm vi của thành viên 2:

- Hái node ở mặt nước, chọn node gần nhất và ưu tiên `id` nhỏ khi hòa.
- Giỏ theo thứ tự thêm vào (LIFO), kiểm tra `hold_capacity` và phát `hold_full`.
- Node mọc lại theo `regrow_s` và phát `node_regrown`.
- Bắt cá dưới nước theo `catch_radius`, yield lấy từ tuning, xóa đàn cá sau khi bắt.
- Cooldown bắt cá lấy từ `catch_cooldown_s`.
- Cập bến ưu tiên trước hái và ghi inventory trong `gather_end`.

Lệnh kiểm tra:

```text
PYTHONPATH=tests:. python3 -m unittest discover -s tests -p 'test_gather*.py' -v
```

Kết quả trên môi trường phát triển: 15 test riêng của gather pass; regression toàn repo hiện tại: 180 test pass. `py_compile` và kiểm tra whitespace cũng pass.
