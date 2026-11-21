# Ma trận truy vết Phase 2 (TICKET-02)

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-2/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| AC-P2-Q1 Quán chuẩn v1.1: bếp B1 [2,8], B2 [5,8]; bàn T1 [9,2], T2 [13,2], T3 [9,6], T4 [13,6] | `tests/test_quan_data_v11.py` + e2e mục 0, 1 (snapshot tick 0 có 2 bếp, 4 bàn) | [quan/unittest.txt](../proof/phase-2/quan/unittest.txt), [quan/e2e-log.txt](../proof/phase-2/quan/e2e-log.txt) | Đạt |
| AC-P2-Q2 6 món đúng công thức, thời gian nấu, giá; 2 nguyên liệu mới `ca_keo`, `keo_neo` đọc được từ file kho | `test_quan_data_v11.py`; e2e mục 2: mọi `cook_started` có `items`/`base_price` khớp menu, khách gọi cả 3 món mới | [quan/e2e-log.txt](../proof/phase-2/quan/e2e-log.txt) | Đạt |
| AC-P2-Q3 `day_plan` D1–D5: `ingredients` = tổng công thức × suất, khớp bảng ticket | `test_quan_data_v11.py` + e2e mục 0 (tính lại từng ngày) | [quan/e2e-log.txt](../proof/phase-2/quan/e2e-log.txt) | Đạt |
| AC-P2-Q4 Khách ngồi bàn trống id nhỏ nhất T1→T4; 4 bàn kín thì bỏ lượt | `tests/test_quan_v11.py` (đến 120/1020/1920/2820 ở T1..T4; lượt khi kín không event) | [quan/unittest.txt](../proof/phase-2/quan/unittest.txt) | Đạt |
| AC-P2-Q5 2 bếp nấu song song; bếp lấy đơn reserved cũ nhất theo order_tick rồi id bàn; interact hòa → bếp trước bàn rồi id | `test_quan_v11.py` + e2e mục 3 (B1 nấu C1, B2 nấu C2, hai bếp cùng `cooking`) | [quan/e2e-log.txt](../proof/phase-2/quan/e2e-log.txt), [quan/hai-bep.json](../proof/phase-2/quan/hai-bep.json) | Đạt |
| AC-P2-Q6 Trong `day`, khách chỉ chọn món trong kế hoạch (lọc trước kho khả dụng); quán chạy riêng dùng cả 6 món | `test_quan_v11.py` (hook `QuanSim(plan_dishes=...)`) | [quan/unittest.txt](../proof/phase-2/quan/unittest.txt) | Đạt ở mức sim. `--mode day` (lát 4) chưa có, nên chưa kiểm qua CLI |
| AC-P2-Q7 Smoke tích hợp `gather --inventory-out` → `quan --inventory` | e2e mục 1 | [quan/e2e-log.txt](../proof/phase-2/quan/e2e-log.txt) | Đạt |
| AC-P2-Q8 Regression P1 với số chuẩn; tất định | Toàn bộ test (124); ca quán 10800 tick chạy 2 lần giống từng byte | [quan/unittest.txt](../proof/phase-2/quan/unittest.txt), [quan/e2e-log.txt](../proof/phase-2/quan/e2e-log.txt) | Đạt. 2 test P1 quán đổi vì chuẩn 4 bàn (lý do trong commit `e8e779d`) |

Chạy lại e2e từ gốc repo: `python3 docs/proof/phase-2/quan/e2e_quan_v11.py <thư-mục-tạm>`.

## Đánh giá ngắn (tại thời điểm Phase 2)
- Yêu cầu nào đạt / chưa đạt: lát 3 (quán 2 bếp/4 bàn, 6 món, kế hoạch ngày) đạt. Các lát khác (số chuẩn gather, cá bơi/sinh, Cá Sấu, `--mode day`, Shop, pause, HUD) thuộc thành viên khác, chưa có trong ma trận này. `contract_version` vẫn là "1.0": nhóm đổi sang "1.1" khi đủ các lát.
- Điều cần chỉnh cho phase sau: lát 4 dựng quán trong `day` cần truyền `plan_dishes` (xem `docs/clarify.md` Q13) và nên kiểm id món kế hoạch thuộc menu. `contract.py` chưa kiểm `stoves`/`tables`/`day_plan`.

## Cập nhật sau integration

Extension `day` hiện đã tồn tại và có test chuyển phase, nhưng đường CLI chưa truyền `plan_dishes` theo `day_plan`; AC-P2-Q6 vẫn chỉ đạt ở mức simulation hook.
