# Retro nhóm

## Phase 1

- Điều tốt: khung headless và Test Contract được giữ ổn định; gather và quán có test riêng; inventory có smoke test xuyên hai tiến trình.
- Điều cần cải thiện: tài liệu kickoff và TEAM.md được cập nhật muộn; ownership của `gather.py` từng giao thoa giữa hai lát.
- Hành động: chốt schema/event trước khi chia task và ghi proof ngay sau mỗi phase.

## Phase 2

- Điều tốt: quán được mở rộng lên 2 bếp, 4 bàn, 6 món và có `day_plan`; bằng chứng e2e được lưu trong `docs/proof/phase-2/`.
- Điều cần cải thiện: extension `day` và HUD chưa được kiểm xuyên CLI trong bằng chứng phase.
- Hành động: thêm test e2e cho session liên tục và cập nhật ma trận truy vết sau mỗi merge.

## Phase 3

- Điều tốt: adapter kho cá thể, độ tươi, giá theo độ tươi và event `spoiled` đã có test deterministic.
- Điều cần cải thiện: gather chưa migration sang kho cá thể nên contract v1.2 chưa bật.
- Hành động: hoàn thành gather v1.2 trước khi đổi `contract_version`, sau đó chạy regression P1–P3.

## Số liệu và bài học

- Kiểm thử hiện tại: 180 test pass sau khi đồng bộ `origin/main`.
- AI cần được review bằng test và diff; các lỗi trước đây gồm payload bếp hiển thị sai và validator thiếu trường fixture.
- Nếu làm lại, nhóm sẽ chốt contract kho và phân công Integrator ngay trong 15 phút đầu.

## Mở đầu retro Phase 4

- Rà lại hành động P2: nhóm đã chốt `day_plan`, giữ hook `plan_dishes` và lưu e2e theo phase; việc còn vướng là contract kho bị bật muộn hơn phần quán.
- Điều làm tốt: v1.3 được tách thành lệnh benchmark/soak/leaderboard, không làm thay đổi JSONL gameplay; các cảnh báo UI có chữ/icon nên vẫn hiểu được khi tắt âm thanh.
- Điều cần sửa: soak hiện chạy bot rỗng nên chưa đo được doanh thu thực tế; cần bot deterministic có gather/serve/shop nếu muốn đánh giá kinh tế nhiều ngày.
- Hành động tiếp theo: hoàn thiện regression fixture v1.3, review artifact trên commit tag và chỉ phát hành sau khi cả 4 thành viên xác nhận.
- Một lỗi AI: đề xuất ban đầu giả định Phase 4 đã có trong repo; nhóm xác minh bằng link, git history và văn bản ticket trước khi viết code.
