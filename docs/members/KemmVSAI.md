# KemmVSAI — phản tư cá nhân

- Tôi đã làm: phần gather resources, survival, hold và inventory hand-off; bằng chứng nằm ở `docs/proof/gather-resources.md` và các test gather.
- Tôi đã giúp: xác nhận ưu tiên cập bến, thứ tự nhặt/bắt, giới hạn túi và dữ liệu chuyển sang buổi quán.
- AI sai ở đâu: dễ bỏ qua điều kiện kho đầy hoặc ghi kho trước khi kết thúc; test boundary và smoke integration đã bắt được các giả định đó.
- Bài học: luật tài nguyên cần kiểm bằng event, snapshot và file bàn giao; chỉ nhìn trạng thái cuối không đủ để phát hiện duplicate.
