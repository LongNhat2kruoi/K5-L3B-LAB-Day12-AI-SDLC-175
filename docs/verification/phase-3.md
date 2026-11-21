# Ma trận truy vết Phase 3 (TICKET-03 "Mùa Nước Nổi")

> Contract trong repo **chưa bật v1.2** (chờ gather, xem [ADR-0001](../adr/0001-kho-ca-the-v1-2.md)). Phần quán và adapter kiểm trong tiến trình với tuning repo + khối `freshness` đúng giá trị TICKET-03.

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-3/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| AC-P3-Q1 File kho cá thể `{id,kind,fresh}`: ghi theo id, đọc lại giữ đúng giá trị và nhánh ở ngưỡng 30 | `tests/test_inventory_v12.py`; e2e mục 1 (7199/240, 30, 7201/240, 97.5) | [quan/e2e-log.txt](../proof/phase-3/quan/e2e-log.txt), [quan/kho-v12.json](../proof/phase-3/quan/kho-v12.json) | Đạt |
| AC-P3-Q2 v1.2 trả mã 2 cho kho đếm, sai schema, kind lạ, id trùng, fresh ngoài miền | `test_inventory_v12.py`, `tests/test_quan_fresh.py`; e2e mục 2 | [quan/unittest.txt](../proof/phase-3/quan/unittest.txt), [quan/e2e-log.txt](../proof/phase-3/quan/e2e-log.txt) | Đạt (adapter + quán). Chưa kiểm qua CLI vì contract repo chưa bật v1.2 |
| AC-P3-Q3 Kho quán hao 0.25/s kể cả hàng giữ; `spoiled` đúng một lần khi ≥30 → <30, theo id | `test_quan_fresh.py`; e2e mục 3 (fresh 30 → tick 1, 7201/240 → tick 2) | [quan/e2e-log.txt](../proof/phase-3/quan/e2e-log.txt) | Đạt |
| AC-P3-Q4 Giữ chỗ theo id (tươi nhất, hòa id); hàng giữ vừa ươn → nhả, giữ lại một lần; thiếu → unfulfillable | `test_quan_fresh.py`; e2e mục 4 (C1 giữ lại I2 sau khi I1 ươn) | [quan/e2e-log.txt](../proof/phase-3/quan/e2e-log.txt) | Đạt |
| AC-P3-Q5 Giá chốt `floor(giá × fresh TB / 100)` khi nấu; boa trên giá đã chốt; `cook_started.items` là cá thể sắp kind rồi id | `test_quan_fresh.py`; e2e mục 4, 5 (mọi `cook_started` trong ca 10800 tick) | [quan/e2e-log.txt](../proof/phase-3/quan/e2e-log.txt), [quan/kho-ca.json](../proof/phase-3/quan/kho-ca.json) | Đạt |
| AC-P3-Q6 Tất định: cùng seed + input + kho → JSONL giống từng byte | e2e mục 5 (chạy 2 lần) | [quan/e2e-log.txt](../proof/phase-3/quan/e2e-log.txt) | Đạt |
| AC-P3-Q7 Regression: chưa bật v1.2 thì đầu ra giữ nguyên | Toàn bộ 176 test (test cũ không sửa); chuỗi event e2e P2 so với bằng chứng Phase 2 | [quan/unittest.txt](../proof/phase-3/quan/unittest.txt), [quan/regression-p2.txt](../proof/phase-3/quan/regression-p2.txt) | Đạt: giống hệt 65 event + dòng end |
| AC-P3-G1 Gather: giỏ cá thể, hao 0.5/s, `spoiled` ở `hold`, bàn giao file v1.2; smoke bàn giao hai tiến trình | — | — | **Chưa đạt**: lát gather chưa làm; contract chưa bật v1.2 (checklist trong ADR-0001) |

Chạy lại e2e từ gốc repo: `python3 docs/proof/phase-3/quan/e2e_quan_v12.py <thư-mục-tạm>`.

## Đánh giá ngắn (tại thời điểm Phase 3)
- Yêu cầu nào đạt / chưa đạt: adapter kho cá thể và quán độ tươi đạt. Smoke bàn giao hai tiến trình v1.2, `day` và HUD chưa kiểm vì gather và lát 4 chưa xong.
- Điều cần chỉnh cho phase sau: gather làm theo checklist trong ADR-0001, rồi bật v1.2 trong một commit, đổi fixture test hộp đen, chạy lại regression P1–P2.

## Cập nhật sau integration

`day` đã được kiểm chứng ở contract hiện hành và có bằng chứng tại `docs/proof/day-mode.md`; phần gather v1.2 và việc bật `contract_version: "1.2"` vẫn chưa hoàn thành.
