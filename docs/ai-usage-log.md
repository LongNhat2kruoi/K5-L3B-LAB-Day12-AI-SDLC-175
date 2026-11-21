# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | Lập kế hoạch từ PRD-0, 3 task (fixture, khách, bếp/phục vụ) mỗi task 1 subagent viết + 1 subagent review, review cuối toàn nhánh, e2e | ≈ 620k token subagent (9 lượt) + phiên điều phối | Review bắt được: crash khi `dish_id` không phải chuỗi, UI hiện `[object Object]` vì bếp đổi sang payload, bếp `cooking` có `ready_ticks > 0` không bị chặn. AI không tự đọc được PRD (lab board khóa theo giờ), người phải dán đề vào. |
| P2 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | TICKET-02 lát 3: dữ liệu v1.1 (2 bếp/4 bàn, 6 món, day_plan, 2 nguyên liệu), hook lọc món theo kế hoạch; 2 task mỗi task 1 viết + 1 review, review cuối, e2e | ≈ 360k token subagent (5 lượt) + phiên điều phối | Bot e2e ban đầu chỉ dùng 1 bếp vì phục vụ nhanh hơn nhịp khách; phải dựng thêm ca 2 khách chờ để kiểm 2 bếp song song. Review nhắc `plan_dishes` chưa kiểm id món, để lát 4 xử lý. |
