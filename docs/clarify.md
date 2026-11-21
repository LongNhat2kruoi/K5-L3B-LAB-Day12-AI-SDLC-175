# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| Q1 | P1 | `no_dish` có tạo khách không? | Không tạo khách, `data = {}` (PRD E: "{} khi có bàn mà thiếu món"). Giả định của nhóm, chưa hỏi Anh Năm. | TV3 (quán) |
| Q2 | P1 | `stove.dish` là id món hay payload? | Payload `{order_id, dish_id, base_price}` giống `hand`, vì PRD D cấm "bếp và tay giữ cùng đơn" nên bếp phải biết `order_id`. | TV3 |
| Q3 | P1 | Khách chưa chốt giá/boa thì `base_price`, `tip` là gì? | `null`. `base_price` chốt ở `cook_started`, `tip` chốt ở `served`. | TV3 |
| Q4 | P1 | `cook_started.items` có lặp theo số lượng không? | Có, sắp theo kind: lẩu → `["bong_dien_dien","ca_linh","ca_linh","ca_linh"]`. | TV3 |
| Q5 | P1 | Kiên nhẫn có giảm khi khách đang ăn? | Không. Kiên nhẫn chỉ giảm khi `waiting`, timer ăn chỉ giảm khi `eating`. | TV3 |
| Q6 | P1 | Hết ca đúng bước khách ăn xong thì lý do trả tiền là gì? | `finished_eating` nếu timer ăn về 0 ở bước đó, còn lại `closing`. Khách chờ rời `closing`, không trừ uy tín. | TV3 |
| Q7 | P1 | Chọn món "đều theo seed" bằng cách nào? | Ứng viên là món đủ nguyên liệu khả dụng, duyệt theo id món (Unicode); chọn bằng `Streams.get("customer_dish").randrange(len)`. | TV3 |
| Q8 | P1 | Bàn gần nhất không tương tác được thì có thử đối tượng kế tiếp? | Không, bỏ lượt (PRD F bước 3). | TV3 |
| Q9 | P1 | Khách fixture có bắt buộc `dish_id`? | Có, mọi trạng thái đơn (kể cả `unfulfillable`) phải có `dish_id` thuộc menu; thiếu → mã 2. | TV3 |
| Q13 | P2 | Quán biết món kế hoạch ngày bằng cách nào khi chạy `--mode day`? | `QuanSim(..., plan_dishes=...)` nhận tập id món của `day_plan[n].dishes`; lát 4 (day) truyền vào khi dựng quán. `None` = quán chạy riêng, dùng cả 6 món (TICKET-02 mục 2). Lọc theo kế hoạch trước, rồi mới lọc kho khả dụng (mục 4.5). | TV3 |
| Q14 | P2 | Trong `day`, khách fixture gọi món ngoài kế hoạch? | Mã 2 lúc dựng quán (TICKET-02 mục 4.3 "món thuộc kế hoạch được kiểm"). | TV3 |
