# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| P1 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | Lập kế hoạch từ PRD-0, fixture, khách, bếp/phục vụ và e2e | ≈ 620k token subagent (9 lượt) + phiên điều phối | Review bắt được lỗi payload bếp, UI hiển thị `[object Object]` và validator thiếu điều kiện `ready_ticks`. |
| P2 | TV3 (quán) | Claude Code: Opus điều phối + subagent Sonnet | TICKET-02: 2 bếp/4 bàn, 6 món, `day_plan`, 2 nguyên liệu và hook lọc món | ≈ 360k token subagent (5 lượt) + phiên điều phối | E2E ban đầu chỉ dùng 1 bếp; review bổ sung ca có 2 khách chờ để kiểm tra nấu song song. |
| P3 | TV3 (quán + adapter kho) | Claude Code: Opus điều phối + subagent Sonnet | TICKET-03: adapter kho cá thể v1.2 (`fresh.py`, đọc/ghi/kiểm hai schema), quán hao tươi, ươn, giữ theo id, giá theo tươi; ADR-0001 + CHANGELOG | ≈ 560k token subagent (5 lượt) + phiên điều phối | Review bắt: khoảng nắn lưới 1e-6 quá rộng có thể kéo 29.999999999 thành 30; NaN/inf trong `freshness` không ra mã 2; bảng tác động trong ADR thiếu test sẽ vỡ khi bật v1.2. |
| P4 | TV3 (Bench/QA) | Claude Code: Opus điều phối + subagent Sonnet | Gỡ cờ `_legacy_compat`, chuyển fixture sang kho cá thể cho 23 test đỏ (regression 190 OK); viết lại benchmark đo khung hình thật trên client Pyxel 1280×720 | ≈ 470k token subagent (5 lượt) + phiên điều phối | Benchmark cũ ghi FPS bằng phép chia, không render. Review của AI bỏ sót lỗi `--out` đường dẫn tương đối (Pyxel đổi thư mục làm việc); người điều phối phát hiện khi chạy đúng lệnh máy chấm. |
| P1–P3 | LongNhat2kruoi | Codex | Đọc toàn repo, triển khai extension `day`, đồng bộ remote và hoàn thiện tài liệu nhóm | Không đo | Đã chạy test sau mỗi thay đổi; phát hiện merge dang dở trước khi pull và hoàn tất bằng merge commit, không reset local. |
| P4 | LongNhat2kruoi | Codex | Contract v1.3, benchmark/soak, leaderboard, accessibility và verification | Không đo | Artifact Phase 4 ban đầu không tải được qua iframe; yêu cầu được xác minh lại từ văn bản ticket người dùng cung cấp. |

Mọi thay đổi do AI đề xuất đều được kiểm tra bằng diff, test và review thủ công trước khi giữ lại.
