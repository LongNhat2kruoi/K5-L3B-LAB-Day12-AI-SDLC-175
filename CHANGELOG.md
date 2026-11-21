# Changelog
## Unreleased

### Breaking (khi bật Contract v1.2 — TICKET-03 "Mùa Nước Nổi")
- **Kho đếm → kho cá thể.** File kho và `scenario.quan.stock` đổi từ `{"items": {kind: n}}` sang `{"items": [{"id", "kind", "fresh"}]}`; kho rỗng là `{"items": []}`. Ở v1.2, file kho đếm, kind lạ, id trùng, `fresh` ngoài [0,100] → mã 2.
- `customers[].reserved` đổi từ map `kind → số` sang mảng id cá thể.
- `cook_started.data.items` đổi từ mảng kind sang mảng cá thể sắp theo kind rồi id.
- Giá món chốt lúc bắt đầu nấu: `base_price = floor(giá niêm yết × trung bình fresh / 100)`; boa tính trên giá đã chốt.
- Event mới `spoiled {item_id, kind, location}` khi cá thể đi từ ≥ 30 xuống < 30.

### Cách bật và chuyển fixture
- Bật v1.2: trong `game.contract.json` đặt `"contract_version": "1.2"` và thêm `tuning.freshness = {"initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30}`. Hai thay đổi phải đi cùng nhau (`load_contract` từ chối nếu thiếu một).
- Đổi fixture: `"stock": {"ca_loc": 2}` → `"stock": [{"id": "I1", "kind": "ca_loc", "fresh": 100}, {"id": "I2", "kind": "ca_loc", "fresh": 100}]`; `"hold": ["ca_loc"]` → `"hold": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]`; `"reserved": {"ca_loc": 1}` → `"reserved": ["I1"]` (id phải có trong `stock`, chưa ươn, đúng công thức theo kind, không trùng với đơn khác).
- Danh sách đầy đủ những chỗ cần đổi khi bật: `docs/adr/0001-kho-ca-the-v1-2.md`, mục "Checklist khi bật v1.2".
- Chưa bật v1.2 thì mọi đầu ra giữ nguyên như Phase 2 (xem ADR-0001).

### Added
- Phase 3: `chonoi/fresh.py` (độ tươi chính xác bằng phân số), adapter đọc/ghi hai schema kho trong `chonoi/inventory.py`, quán hao tươi 0.25/s, hàng ươn, giữ chỗ theo id và giữ lại khi hàng vừa ươn, giá theo độ tươi. Gather (giỏ cá thể, hao 0.5/s) chưa làm.
- Phase 2: quán 2 bếp/4 bàn, 6 món, `day_plan` D1–D5, nguyên liệu `ca_keo`, `keo_neo`; hook lọc món theo kế hoạch ngày.
- Phase 1: luật quán (khách, giữ chỗ, kiên nhẫn, bếp, phục vụ, tiền, boa, uy tín).
