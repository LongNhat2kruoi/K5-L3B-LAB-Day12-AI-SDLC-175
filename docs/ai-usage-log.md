# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | Lập kế hoạch từ PRD-0, fixture, khách, bếp/phục vụ và e2e | ≈ 620k token subagent (9 lượt) + phiên điều phối | Review bắt được lỗi payload bếp, UI hiển thị `[object Object]` và validator thiếu điều kiện `ready_ticks`. |
| P2 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | TICKET-02: 2 bếp/4 bàn, 6 món, `day_plan`, 2 nguyên liệu và hook lọc món | ≈ 360k token subagent (5 lượt) + phiên điều phối | E2E ban đầu chỉ dùng 1 bếp; review bổ sung ca có 2 khách chờ để kiểm tra nấu song song. |
| P1–P3 | LongNhat2kruoi | Codex | Đọc toàn repo, triển khai extension `day`, đồng bộ remote và hoàn thiện tài liệu nhóm | Không đo | Đã chạy test sau mỗi thay đổi; phát hiện merge dang dở trước khi pull và hoàn tất bằng merge commit, không reset local. |

Mọi thay đổi do AI đề xuất đều được kiểm tra bằng diff, test và review thủ công trước khi giữ lại.
