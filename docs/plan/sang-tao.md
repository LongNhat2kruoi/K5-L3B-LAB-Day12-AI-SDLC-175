# Phần riêng: Giao diện và Sáng tạo (đề xuất)

## Phạm vi đề xuất với trưởng nhóm

Tôi nhận vai 4 (tích hợp, kiểm thử, phát hành). Theo `docs/plan/team-work-plan.md`, vai này giữ `chonoi/web/index.html` và HUD, nên phần giao diện và sáng tạo nằm trong vai của tôi.

Phần này an toàn với chấm tự động vì cửa sổ chơi (`chonoi/live.py`) chỉ đọc trạng thái và sự kiện qua `GET /state`; trình duyệt không ghi gì vào mô phỏng ngoài phím bấm của người chơi. Mọi thứ dưới đây chỉ chạy trong trình duyệt nên headless không đổi một byte nào. Bằng chứng: chạy lại smoke test và so file JSONL trước và sau khi thêm.

Luật cố định của PRD (số liệu, 3 món, 4 nguyên liệu, 1 bếp, 1 bàn) không được đổi, nên "lối chơi thêm" ở đây là những gì giúp người chơi hiểu, quyết định và thấy vui hơn, không phải luật mới.

## Ý tưởng

| # | Ý tưởng | Đọc từ đâu | Người chơi được gì | Công sức |
|---|---|---|---|---|
| 1 | Má Tư nhắc việc: "Bếp chín rồi con!" khi món chín, "Khách sốt ruột kìa!" khi kiên nhẫn dưới 50 % (đúng ngưỡng mất tiền boa) | sự kiện `dish_ready`, `patience_ticks_left` | Biết lúc nào phải chạy, như một hướng dẫn chơi | nhỏ |
| 2 | Màn chuyển buổi: hoàng hôn, kể kho mang về và món nấu được ("Hôm nay đủ đồ nấu Lẩu cá linh!") | sự kiện `gather_end` | Hiểu sáng lặn gì thì tối bán được gì | nhỏ |
| 3 | Âm thanh tự tạo bằng WebAudio (bọt nước, bếp xèo, chuông khách, tiền rơi), không dùng file ngoài nên không vướng bản quyền | các sự kiện | Cảm giác sống động | nhỏ |
| 4 | Báo động oxy: bọt khí, màn hình tối dần, tiếng tim đập khi oxy dưới 25 % | `oxygen_ticks` | Né bị ngạt mà không phải nhìn thanh oxy | nhỏ |
| 5 | Khách có tên và tính cách, bong bóng thoại đổi theo kiên nhẫn (vui, sốt ruột, giận) | `customers[]` | Quán có người thật, dễ thấy ai sắp bỏ đi | vừa |
| 6 | Sổ tay sông nước: lần đầu bắt mỗi loài cá, hái mỗi loại bông thì mở một trang giới thiệu ngắn (lưu trong trình duyệt) | `fish_caught`, `gather` | Mục tiêu sưu tầm, học về đặc sản miền Tây | vừa |
| 7 | Bảng tổng kết cuối ngày kèm danh hiệu ("Thợ lặn cừ", "Quán đông khách", "Không để khách nào bỏ về") | `quan_end` và sự kiện trong ca | Lý do chơi lại để đạt danh hiệu khác | vừa |
| 8 | Chuỗi phục vụ nhanh: phục vụ có boa liên tiếp hiện "Nhanh tay x3!" (chỉ hiển thị, không cộng tiền) | `served` có `tip > 0` | Thưởng cảm giác khi chơi giỏi | nhỏ |
| 9 | Hình vẽ 2D thật: Út Sen áo bà ba, khăn rằn; đàn cá lắc lư tại chỗ; nhà bè có đèn và khói bếp | snapshot | Đúng phong cách PRD mục 3 | lớn |

Đề xuất làm trước: 1, 2, 3 (nhỏ, thấy rõ, mỗi ý là một commit). Sau đó: 4, 7. Còn giờ thì 5, 6, 9.

## Rủi ro

- Phụ thuộc tên sự kiện và trường snapshot của vai 1, 2, 3: cần bảng sự kiện vai 4 chốt trước. Khi trường chưa có, giao diện tự bỏ qua (khung đã làm vậy).
- Không thêm phím gửi vào mô phỏng; mọi điều khiển mới (bật/tắt âm thanh, mở sổ tay) xử lý hoàn toàn trong trình duyệt.

## Trạng thái thực hiện

- Đã có bản chơi `play/index.html`, sprite bơi/quán và HUD/menu/pause trong `play/main.py`.
- Đã có extension `day` ở simulation; chuyển phase được kiểm chứng headless và live.
- Các ý tưởng hội thoại, sổ tay, huy hiệu và âm thanh WebAudio vẫn là backlog UI; không được xem là tiêu chí headless đã hoàn thành.
