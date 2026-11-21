# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | Lập kế hoạch từ PRD-0, 3 task (fixture, khách, bếp/phục vụ) mỗi task 1 subagent viết + 1 subagent review, review cuối toàn nhánh, e2e | ≈ 620k token subagent (9 lượt) + phiên điều phối | Review bắt được: crash khi `dish_id` không phải chuỗi, UI hiện `[object Object]` vì bếp đổi sang payload, bếp `cooking` có `ready_ticks > 0` không bị chặn. AI không tự đọc được PRD (lab board khóa theo giờ), người phải dán đề vào. |
