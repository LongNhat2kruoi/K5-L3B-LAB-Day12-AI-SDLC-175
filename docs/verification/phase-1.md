# Ma trận truy vết Phase 1

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| AC-P1-Q1 Fixture quán theo PRD D: mặc định khách, cấp `reserved`, mã 2 cho mâu thuẫn | `tests/test_quan_fixture.py` (27 ca, hộp đen qua headless) | [quan/unittest.txt](../proof/phase-1/quan/unittest.txt) | Đạt |
| AC-P1-Q2 Khách đến theo lịch (tick 120, rồi mỗi 900 tick), bàn trống id nhỏ nhất, chọn món theo seed trong món đủ kho khả dụng, `no_dish` | `tests/test_quan_customers.py` + e2e (khách đầu tick 120; lượt 1020 bỏ vì bàn còn người) | [quan/unittest.txt](../proof/phase-1/quan/unittest.txt), [quan/e2e-log.txt](../proof/phase-1/quan/e2e-log.txt) | Đạt |
| AC-P1-Q3 Giữ chỗ nguyên liệu khi gọi; kho khả dụng = tồn − giữ | unit test 2 bàn trong `test_quan_customers.py` | [quan/unittest.txt](../proof/phase-1/quan/unittest.txt) | Đạt |
| AC-P1-Q4 Hết kiên nhẫn → `customer_left patience`, uy tín −0.5; hết ca → khách chờ rời `closing`, không trừ uy tín, rồi `quan_end` | `test_quan_customers.py` | [quan/unittest.txt](../proof/phase-1/quan/unittest.txt) | Đạt |
| AC-P1-Q5 Nấu → bưng → phục vụ → trả tiền đúng tick (nấu `cook_s×60`, ăn 600), boa `floor(giá×0.2)` khi kiên nhẫn ≥ 50%, uy tín +0.2 | `tests/test_quan_service.py` (18 ca) + e2e một ca quán 10800 tick bằng input thật | [quan/e2e-log.txt](../proof/phase-1/quan/e2e-log.txt), [quan/quan-inputs.json](../proof/phase-1/quan/quan-inputs.json) | Đạt: 6 đơn, money 432, uy tín 4.2, score 832 |
| AC-P1-Q6 Một interact mỗi bước, chọn theo (khoảng cách, bếp trước bàn, id); tính cả đúng mép bán kính | `test_quan_service.py` | [quan/unittest.txt](../proof/phase-1/quan/unittest.txt) | Đạt |
| AC-P1-Q7 Tất định: cùng seed + input → JSONL giống từng byte | e2e chạy headless 2 lần, so byte | [quan/e2e-log.txt](../proof/phase-1/quan/e2e-log.txt) | Đạt |
| AC-P1-G1 Smoke hai tiến trình (PRD G): gather ghi kho, quán đọc đúng `stock` | e2e phần 1 + `test_smoke_p1.py` | [quan/e2e-log.txt](../proof/phase-1/quan/e2e-log.txt) | Đạt |

Chạy lại e2e từ gốc repo: `python3 docs/proof/phase-1/quan/e2e_quan.py <thư-mục-tạm>`.

## Đánh giá ngắn
- Yêu cầu nào đạt / chưa đạt: phần quán (lát 3 + 4) đạt toàn bộ các AC ở trên, 89 test xanh ở commit ghi trong `unittest.txt`. Phần gather (lát 1–2), HUD và tag `phase-1` thuộc thành viên khác, chưa kiểm ở đây.
- Điều cần chỉnh cho phase sau: các giả định Q1–Q9 trong `docs/clarify.md` chưa được Anh Năm xác nhận; nên hỏi trước khi chốt tag. Trên Windows cần lệnh `python3` (hoặc đổi `headless_cmd`) và `PYTHONUTF8=1` để log test sạch.
