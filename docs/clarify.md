# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 | Có thể chơi gather và quan trong cùng một màn không? | Có. Giữ nguyên hai mode độc lập để tương thích Test Contract; thêm extension `day` chuyển inventory trong bộ nhớ sau `gather_end`, không dùng file kho trung gian. | Tech Lead |
| Q1 | P1 | `no_dish` có tạo khách không? | Không tạo khách, `data = {}` (PRD E: "{} khi có bàn mà thiếu món"). Giả định của nhóm, chưa hỏi Anh Năm. | TV3 (quán) |
| Q2 | P1 | `stove.dish` là id món hay payload? | Payload `{order_id, dish_id, base_price}` giống `hand`, vì PRD D cấm "bếp và tay giữ cùng đơn" nên bếp phải biết `order_id`. | TV3 |
| Q3 | P1 | Khách chưa chốt giá/boa thì `base_price`, `tip` là gì? | `null`. `base_price` chốt ở `cook_started`, `tip` chốt ở `served`. | TV3 |
| Q4 | P1 | `cook_started.items` có lặp theo số lượng không? | Có, sắp theo kind: lẩu → `["bong_dien_dien","ca_linh","ca_linh","ca_linh"]`. | TV3 |
| Q5 | P1 | Kiên nhẫn có giảm khi khách đang ăn? | Không. Kiên nhẫn chỉ giảm khi `waiting`, timer ăn chỉ giảm khi `eating`. | TV3 |
| Q6 | P1 | Hết ca đúng bước khách ăn xong thì lý do trả tiền là gì? | `finished_eating` nếu timer ăn về 0 ở bước đó, còn lại `closing`. Khách chờ rời `closing`, không trừ uy tín. | TV3 |
| Q7 | P1 | Chọn món "đều theo seed" bằng cách nào? | Ứng viên là món đủ nguyên liệu khả dụng, duyệt theo id món (Unicode); chọn bằng `Streams.get("customer_dish").randrange(len)`. | TV3 |
| Q8 | P1 | Bàn gần nhất không tương tác được thì có thử đối tượng kế tiếp? | Không, bỏ lượt (PRD F bước 3). | TV3 |
| Q9 | P1 | Khách fixture có bắt buộc `dish_id`? | Có, mọi trạng thái đơn (kể cả `unfulfillable`) phải có `dish_id` thuộc menu; thiếu → mã 2. | TV3 |
| Q10 | P2 | Phase 2 quán có mấy bếp, mấy bàn, bao nhiêu khách? | Theo TICKET-02: 2 bếp, 4 bàn. Mỗi bàn 1 khách, tối đa 4 khách ngồi cùng lúc; bàn kín thì khách mới không vào. Khách tới cách nhau 10 s (khoảng 18 khách/ca 180 s). | Nhóm |
| Q11 | P2 | Bước nhận order (phần sáng tạo của nhóm) chạy thế nào? | Khách vào cửa góc dưới phải, ngồi bàn, chờ 10 s để Út Sen tới bàn bấm E nhận order. Quá 10 s khách giận và chỉ còn 5 s; hết 5 s mà chưa ai nhận thì khách bỏ về, uy tín −0.5 (như hết kiên nhẫn). Nhận order lúc khách đang giận thì không có boa. Gợi ý cho luật: khách có `state: "ordering"`, `order_ticks_left`, `angry`; event `order_taken {order_id, table_id, late}`; `customer_left.reason = "no_order"`. Đây là phần sáng tạo nên **tắt ở headless/test chấm** (AGENTS.md): bật bằng một khóa tuning riêng, mặc định tắt, chỉ bản chơi bật. | Nhóm |
| Q12 | P2 | Kiên nhẫn chờ món tính từ lúc nào, bao lâu? | Từ lúc nhận order. Đang chọn giữa 30 s và 45 s. Đề xuất 45 s: 4 bàn mà chỉ 1 người bưng, khách gọi sau cùng có thể phải chờ 35–40 s. Chờ chốt. | Nhóm (chưa chốt) |
