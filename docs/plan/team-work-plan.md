# Kế hoạch phân công 4 thành viên

Kế hoạch này bám theo `team_size: 4` trong `game.contract.json`. Mỗi thành viên sở hữu một vùng file chính; các file contract và khung dùng chung chỉ được thay đổi sau khi cả nhóm thống nhất.

## Phân công tổng quan

| Thành viên | Mảng phụ trách chính | File/thư mục sở hữu độc quyền | Deliverables |
|---|---|---|---|
| Thành viên 1 — Gather Gameplay | Luật lặn, oxy, máu và giỏ | `chonoi/sim/gather.py`, `tests/test_gather_rules.py` | Oxy, ngạt, faint, giỏ LIFO, sự kiện gather và test luật |
| Thành viên 2 — Gather Resources | Hái nút, bắt cá và cân bằng gather | `chonoi/sim/gather.py` (phối hợp với Thành viên 1), `tests/test_gather_resources.py` | Hái, regrow, bắt cá, cooldown, `hold_full`, inventory và test tương tác |
| Thành viên 3 — Quán Gameplay | Khách, bếp, món và thanh toán | `chonoi/sim/quan.py`, `tests/test_quan_rules.py` | State machine khách/bếp, nấu món, phục vụ, tiền, boa, uy tín |
| Thành viên 4 — Integration / QA / Release | Contract integration, UI, E2E và tài liệu | `tests/test_integration.py`, `chonoi/web/index.html`, `docs/`, `TEAM.md`, `CHANGELOG.md`, `CREDITS.md` | Chốt schema/event, test E2E, HUD, bằng chứng, tag và release |

> `chonoi/sim/gather.py` là vùng phối hợp duy nhất giữa Thành viên 1 và 2. Hai người phải thống nhất interface/event trước, chia commit theo lát nhỏ và không sửa cùng một đoạn trong cùng thời điểm.

## Lộ trình thực hiện

### Phase 1 — Nền tảng và chạy song song

- Thành viên 1 triển khai lifecycle người chơi: di chuyển, oxy, ngạt, máu, faint và giỏ.
- Thành viên 2 triển khai node/fish interaction: hái, regrow, bắt cá và cooldown.
- Thành viên 3 thiết kế state machine cho `QuanSim`, khách và bếp; viết test fixture.
- Thành viên 4 chốt bảng event/schema trong `docs/contracts/README.md`, bổ sung test E2E và cập nhật hồ sơ nhóm.

### Phase 2 — Tích hợp và kết nối

Thống nhất trước khi merge:

- Event có dạng `type`, `tick`, `phase`, `name`, `data`.
- `gather_end` là điểm duy nhất ghi inventory.
- `quan` không nhận đồng thời `--inventory` và `scenario.stock`.
- Mọi tuning lấy từ `game.contract.json`; mọi danh sách entity được sắp bằng `sort_by_id`.
- Mỗi tick tối đa một thao tác `interact`.

Event tối thiểu cần giữ ổn định:

```text
gather: dive, surface, oxygen_empty, choke, faint, gather,
        node_regrown, hold_full, fish_caught, gather_end
quan:   customer_arrived, no_dish, cook_started, dish_ready,
        dish_picked, served, customer_left, paid, quan_end
```

### Phase 3 — Kiểm thử, tối ưu và đóng gói

- Chạy `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`.
- Kiểm tra deterministic output với cùng seed/input.
- Kiểm tra luồng `gather --inventory-out` → `quan --inventory`.
- Chạy thử live browser và rà HUD/event log.
- Hoàn thiện `docs/proof/`, `docs/verification/`, `docs/ai-usage-log.md`, `docs/retro.md` và hồ sơ thành viên.
- Thành viên 4 chịu trách nhiệm gắn tag `phase-1` đến `phase-4` và chuẩn bị `v1.0.0` sau khi nhóm duyệt.

## Git và chống xung đột

Đề xuất branch:

```text
feature/gather-survival
feature/gather-resources
feature/quan-gameplay
feature/integration-qa-release
```

Các file cần cả nhóm thống nhất trước khi sửa:

```text
game.contract.json
docs/contracts/README.md
docs/contracts/inventory.sample.json
chonoi/runner.py
chonoi/scenario.py
chonoi/inventory.py
tests/test_smoke_p1.py
```

Mỗi PR phải ghi mục tiêu, file thay đổi, lệnh test, kết quả test và rủi ro còn lại. Không sửa test chỉ để làm xanh khi luật chưa đúng.
