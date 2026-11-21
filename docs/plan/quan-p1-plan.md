# Kế hoạch Phase 1 — Quán (TV3: lát 3 + lát 4)

**Spec:** [docs/prd/prd-0.md](../prd/prd-0.md) — mục D (fixture quán), E (snapshot/event quán), F "Quán" (5 bước), G (kho).
**Phạm vi:** `chonoi/sim/quan.py`, kiểm schema khối `quan` trong `chonoi/scenario.py`, test mới `tests/test_quan_*.py`. Không đụng gather.

## Global Constraints (mọi task)
- Python 3 chỉ thư viện chuẩn. Số liệu đọc từ `tuning` (`game.contract.json`); không hard-code 60, 3600, 600, giá, công thức… (ngoại lệ: hằng `TICK = 60` đã có).
  Quy đổi: `patience_max = round(patience_s*60)`, `eat_max = round(eat_s*60)`, `cook_ticks = round(menu[d]["cook_s"]*60)`, `interval = round(customer_interval_s*60)`.
- Ngẫu nhiên chỉ qua `self.rng.get("customer_dish")` (Streams). Không `random` toàn cục, không đồng hồ. Cùng seed → JSONL giống từng byte.
- Danh sách thực thể sắp bằng `ids.sort_by_id`; id khách mới cấp bằng `self.ids.new("C")`. Duyệt món theo id món sắp mã Unicode (`sorted(menu)`).
- Lỗi fixture/mâu thuẫn → `raise BadInput(...)` (`chonoi/errors.py`) lúc dựng (trước khi ghi JSONL) → mã 2.
- Event là tuple `(name, data_dict)` trả từ `step()`; runner gắn tick. Tên và khóa `data` đúng mục E.
- Không sửa `runner.py`, `inventory.py`, `contract.py`, `game.contract.json`, `tests/test_smoke_p1.py`. Toàn bộ test phải xanh:
  `PYTHONPATH=tests:. python3 -m unittest discover -s tests -v`.
- Test mới viết kiểu hộp đen qua `helpers.run_headless` (như `tests/test_smoke_p1.py`); có thể thêm unit test gọi thẳng `QuanSim`.

## Quyết định cho chỗ PRD chưa rõ (ghi lại trong docs/clarify.md)
- R1 `no_dish`: không tạo khách, `data = {}`.
- R2 `stove.dish` và `hand` đều là payload `{order_id, dish_id, base_price}` hoặc `null`.
- R3 Khách chưa chốt giá/boa: `base_price = null`, `tip = null`. `base_price` chốt khi `cook_started` (= `menu[dish].price`); `tip` chốt khi `served`.
- R4 `cook_started.items`: mảng kind lặp theo số lượng, sắp theo kind (vd lẩu → `["bong_dien_dien","ca_linh","ca_linh","ca_linh"]`).
- R5 Bước 1: kiên nhẫn chỉ giảm cho khách `waiting`; timer ăn chỉ giảm cho khách `eating`; tất cả kẹp ≥ 0.
- R6 Bước 4 lúc hết ca (`time_left_ticks == 0` sau bước 1): theo id bàn — khách `eating` có `eat_ticks_left == 0` trả `finished_eating`; khách `eating` còn lại trả `closing`; khách `waiting` rời `closing`, không đổi uy tín. Rồi `quan_end`, `done = True`, `reason = "time"`, không sinh khách.
- R7 Khách `customer_left` mang `reputation` sau khi đổi (closing: giá trị hiện tại).
- R8 Lịch khách: khi `random_customers` (mặc định true), còn giờ, và `phase_tick >= first_customer_tick` và `(phase_tick - first_customer_tick) % interval == 0`.
- R9 Chọn món: ứng viên = `sorted(menu)` lọc món có `available[k] >= recipe[k]` với mọi k, `available = stock − tổng reserved`; chọn `cands[rng.get("customer_dish").randrange(len(cands))]`.
- R10 Tip: `ratio = patience_ticks_left / patience_max` (giá trị sau bước 1); `tip = floor(base_price * tip_rate)` nếu `ratio >= tip_min_patience_ratio`, ngược lại 0.
- R11 Bàn tương tác được khi tay có payload và khách ngồi bàn đó có `id == hand.order_id`, `state == "waiting"`. Đối tượng gần nhất không tương tác được → bỏ lượt (không thử đối tượng khác).
- R12 Khách fixture: `dish_id` bắt buộc (món trong menu) cho mọi trạng thái đơn.

---

## Task 1: Fixture quán (mục D) — schema + dựng trạng thái + kiểm mâu thuẫn

**Files:** `chonoi/scenario.py` (`_validate_quan`), `chonoi/sim/quan.py` (`__init__`, `snapshot`), tạo `tests/test_quan_fixture.py`.

**Schema (scenario.py, chỉ kiểm hình dạng, không cần kho):**
- `random_customers`: bool. `reputation`: số trong `[reputation_min, reputation_max]`.
- `stoves[]` khóa cho phép `{id,pos,state,dish,cook_ticks_left,ready_ticks}`; `tables[]` khóa `{id,pos}`; id bếp/bàn phải có trong tuning (đã có kiểm ở sim `_merge`, giữ nguyên). `pos` trong `bounds` quán (trục x,z). `state ∈ {idle,cooking,ready}`. `cook_ticks_left`, `ready_ticks` nguyên ≥ 0. `dish` là payload hoặc null.
- Payload (`dish`, `hand`): object đúng 3 khóa `order_id` (chuỗi), `dish_id` (trong menu), `base_price` (nguyên > 0); hoặc null.
- `customers[]` khóa cho phép `{id,table_id,dish_id,order_tick,state,patience_ticks_left,eat_ticks_left,order_status,reserved,base_price,tip}`. `dish_id` bắt buộc, thuộc menu. `state ∈ {waiting,eating}`. `order_status ∈ {reserved,assigned,unfulfillable,served}`. `order_tick` nguyên ≥ 0. `patience_ticks_left` nguyên trong `[0, patience_max]`. `eat_ticks_left` nguyên trong `[0, eat_max]`. `reserved`: object kind (`KINDS_P1`) → nguyên ≥ 0. `base_price`, `tip`: nguyên ≥ 0 hoặc null (base_price nếu có phải > 0). `table_id` có thật, khách không trùng bàn (đã có).

**Dựng (QuanSim.__init__)** — khách mặc định: `state "waiting"`, `order_tick 0`, `patience_ticks_left = patience_max`, `eat_ticks_left 0`, `order_status "reserved"`, `base_price null`, `tip null`. Snapshot khách chỉ gồm đúng 11 khóa ở trên. Đơn `reserved` thiếu `reserved` → cấp đúng công thức, xét theo `(order_tick, id_key(table_id))`; đơn không phải `reserved` thiếu `reserved` → `{}`. Bỏ khóa lượng 0 trong `reserved`.

**Mâu thuẫn → BadInput (trong __init__, cần kho):**
- Đơn `reserved`: `reserved` khác công thức món → lỗi. Tổng giữ theo kind > `stock[kind]` → lỗi ("quá tồn").
- `state == "eating"` ⇔ `order_status == "served"`; khách eating cần `eat_ticks_left > 0` và `base_price`, `tip` là số nguyên. Khách waiting cần `eat_ticks_left == 0`.
- Đơn `assigned`: `reserved` rỗng, có **đúng một** món trong (bếp `cooking`/`ready`) ∪ (tay) có `order_id` bằng id khách, `dish_id` khớp.
- Đơn `unfulfillable`/`served`: `reserved` rỗng, không có món nào trỏ tới.
- Bếp `idle`: `dish null`, `cook_ticks_left 0`, `ready_ticks 0`. Bếp `cooking`: `dish` khác null, `cook_ticks_left > 0`. Bếp `ready`: `dish` khác null, `cook_ticks_left 0`.
- Payload ở bếp/tay trỏ tới `order_id` không có khách → lỗi ("liên kết thiếu"); trỏ tới đơn không `assigned` → lỗi; `dish_id` khác `dish_id` của khách → lỗi; hai nơi giữ cùng đơn → lỗi.

**Snapshot:** thêm `vel` vào `player` (`{"pos":…, "vel":…}`). Giữ phần còn lại.

**Tests (tests/test_quan_fixture.py, ≥ 12 ca):** mỗi ca mã 2 ở trên một ca (khóa lạ khách, dish_id lạ, state lạ, giữ khác công thức, giữ quá tồn, assigned không món, bếp+tay cùng đơn, payload trỏ khách không có, bếp cooking timer 0, eating thiếu base_price, reputation ngoài miền, random_customers không bool); ca hợp lệ: khách thiếu `reserved` được cấp đúng công thức và snapshot tick 0 có đủ 11 khóa + giá trị mặc định; ca `--ticks 0` không có khách → `customers: []`; ca player snapshot có `vel`.

## Task 2: Lát 3 — khách, giữ chỗ, kiên nhẫn, hết ca

**Files:** `chonoi/sim/quan.py` (`step` + helper), tạo `tests/test_quan_customers.py`.

Thêm `self.phase_tick = 0` (tăng 1 đầu mỗi `step`). `self.random_customers = scenario.get("random_customers", True)`. Viết `step()` theo đúng 5 bước F "Quán" (bước 2–3 về bếp/interact để chỗ trống `# lát 4` cho Task 3, nhưng **giữ thứ tự gọi**):
1. `phase_tick += 1`; `time_left_ticks = max(0, -1)`; khách waiting: `patience -1` (kẹp 0); khách eating: `eat -1` (kẹp 0). (Bếp: Task 3.)
2–3. Di chuyển (`_move` đã có). Interact: Task 3.
4. Theo id bàn (`sort_by_id` khách theo `table_id`): nếu còn giờ — khách waiting có `patience_ticks_left == 0` rời: `reputation = clamp(reputation + left_reputation_delta)`, event `customer_left {order_id, table_id, reason:"patience", reputation}`, xóa khách (nhả `reserved`; bỏ món của đơn trên bếp → bếp `idle` dish null timers 0; trên tay → `hand = null`). Nếu hết giờ: R6 (phần trả tiền làm ở Task 3; Task 2 làm phần khách waiting rời `closing` và `quan_end {reason:"time", money, earned, shift_earned, reputation}`).
5. Nếu còn giờ: R8 lịch; không bàn trống → bỏ lượt (không event); bàn trống id nhỏ nhất; R9 chọn món; không có → `no_dish {}`; có → khách mới id `ids.new("C")`, `order_tick = phase_tick`, `reserved = công thức`, các trường mặc định như Task 1, event `customer_arrived {order_id, table_id, dish_id}`.
Helper chung: `_available()` = stock − tổng reserved; `_remove_customer(c)` dọn món/tay/bếp.

**Tests (≥ 8 ca, hộp đen):** khách đầu đến đúng tick 120 với preset (`stock` đủ, scenario `stock`), lần sau 120+900; `order_tick` = 120; stock không đủ món nào → `no_dish {}` và không có khách; bàn đầy → không event ở lượt sau; khách giữ chỗ làm món khác không chọn được (vd stock `ca_loc:1` + 2 lượt khách mà bàn đã trống lại → no_dish); khách hết kiên nhẫn: fixture khách `patience_ticks_left: 5`, `random_customers:false` → `customer_left` reason patience ở tick 5, uy tín 3.0 → 2.5; hết ca với khách waiting (`time_left_ticks: 3`) → `customer_left closing`, uy tín không đổi, rồi `quan_end` ở tick 3, dòng end reason `time`; cùng seed hai lần → JSONL giống byte; seed khác nhau có thể chọn món khác (chỉ kiểm món thuộc ứng viên hợp lệ).

## Task 3: Lát 4 — bếp, interact, bưng, phục vụ, trả tiền, boa, uy tín

**Files:** `chonoi/sim/quan.py`, tạo `tests/test_quan_service.py`.

1. Bước 1 thêm: bếp `cooking` `cook_ticks_left -1` (kẹp 0); bếp `ready` từ **đầu bước** `ready_ticks +1`.
2. Bước 2: duyệt bếp theo id; `cooking` có `cook_ticks_left == 0` → `ready`, `ready_ticks = 0`, event `dish_ready {stove_id, order_id, dish_id}`.
3. Sau `_move`, nếu `inp.pressed("interact")`: ứng viên = bếp và bàn có `dist(player, pos) <= interact_radius`; chọn min theo `(dist, 0 nếu bếp / 1 nếu bàn, id_key(id))`. Không tương tác được → bỏ lượt (R11).
   - Bếp `idle`: đơn `reserved` cũ nhất theo `(order_tick, id_key(table_id))`; không có → bỏ lượt. Trừ `stock` đúng `reserved` (bỏ khóa về 0), `reserved = {}`, `order_status = "assigned"`, `base_price = menu price`, bếp `cooking`, `dish = payload`, `cook_ticks_left = cook_ticks`. Event `cook_started {stove_id, order_id, dish_id, items (R4), base_price}`.
   - Bếp `ready` + tay trống (`hand is None`, `carry_limit` 1): `hand = dish`, bếp `idle` (dish null, timers 0). Event `dish_picked {stove_id, order_id, dish_id}`.
   - Bàn (R11): khách `state "eating"`, `order_status "served"`, `eat_ticks_left = eat_max`, `tip` theo R10, `base_price` từ payload, `hand = None`. Event `served {order_id, table_id, dish_id, patience_ticks_left, base_price, tip}`.
4. Trước phần rời của Task 2, cùng vòng theo id bàn: khách `eating` có `eat_ticks_left == 0` → trả `finished_eating`. Hết giờ: khách eating còn lại trả `closing` (R6). Trả tiền: `amount = base_price + tip`; `money`, `earned`, `shift_earned` cộng `amount`; `tip > 0` → `reputation = clamp(reputation + tip_reputation)`; event `paid {order_id, table_id, base_price, tip, amount, reason}`; xóa khách.

**Tests (≥ 8 ca):** dựng fixture đặt player cạnh bếp (`player.pos` = `[2,8]`) với khách T1 dish `goi_bong_sung`, stock `bong_sung:2`, `random_customers:false`; interact → `cook_started` items `["bong_sung","bong_sung"]`, base_price 40, stock về `{}`; sau 240 tick → `dish_ready` đúng tick; interact lần nữa → `dish_picked`, hand payload; đi tới bàn (đặt lại player qua fixture riêng với `hand` + bếp idle + khách assigned) → `served` tip = floor(40*0.2)=8 khi kiên nhẫn đầy, tip 0 khi `patience_ticks_left` < 1800; trả tiền sau 600 tick `paid finished_eating amount 48`, uy tín 3.0→3.2, money/earned 48; hết ca khi đang ăn → `paid closing`; bếp gần hơn bàn được chọn trước, cùng khoảng cách bếp trước bàn; khách rời khi món đang nấu → bếp về idle, stock không hoàn; tay đầy thì bếp ready bỏ lượt.

## Sau Task 3 (controller): kiểm chứng toàn quy trình
Smoke hai tiến trình (mục G), lượt quán đầy đủ có input thật (nấu → bưng → phục vụ → trả), tất định, toàn bộ test; lưu kết quả vào `docs/proof/phase-1/`, cập nhật `docs/verification/phase-1.md`, `docs/clarify.md`, `docs/ai-usage-log.md`.
