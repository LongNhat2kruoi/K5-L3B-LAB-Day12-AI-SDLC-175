# ADR-0001: Chuyển kho đếm sang kho cá thể có độ tươi (Contract v1.2)

- Trạng thái: chấp nhận (phần adapter + quán); chờ gather để bật v1.2
- Ngày, người quyết: Phase 3 (TICKET-03), quangpham (TV3), cần cả nhóm xác nhận thứ tự bật

## Bối cảnh
TICKET-03 thay kho `{"items": {kind: n}}` bằng mảng cá thể `{"items": [{id, kind, fresh}]}`. Độ tươi hao theo tick (giỏ 0.5/s, kho quán 0.25/s), hàng `fresh < 30` bị ươn, giữ chỗ theo id, giá chốt theo độ tươi. Bên đọc chọn schema theo `contract_version`; ở v1.2 file kho đếm phải trả mã 2. Hai đầu (gather ghi kho, quán đọc kho) do người khác nhau làm và không xong cùng lúc, trong khi `main` phải luôn chạy được.

## Các lựa chọn đã cân nhắc
1. **Đổi một lần sang v1.2** (contract, gather, quán trong cùng một lần merge). Đơn giản, nhưng `main` vỡ cho tới khi mọi lát xong; người làm trước bị chặn.
2. **Hai phiên bản nội bộ, bật bằng contract** (đề gợi ý). Adapter đọc/ghi cả hai schema; luật chọn theo cờ. `main` giữ schema đếm tới khi hai đầu sẵn sàng rồi bật trong một commit.
3. **Số thực cho độ tươi.** Dễ viết, nhưng sai số làm lệch nhánh ở ngưỡng 30 và phép floor giá.

## Quyết định
- Chọn **lựa chọn 2**. Cờ: schema cá thể bật khi `tuning` có khối `freshness`; `load_contract` bắt buộc `contract_version == "1.2"` khi và chỉ khi có `freshness`. Repo giữ phiên bản hiện tại (`"1.0"`, nhóm chưa đổi sang `"1.1"` ở Phase 2) cho tới khi gather xong; bật v1.2 = đổi version + thêm `freshness {initial:100, gather_decay_per_s:0.5, quan_decay_per_s:0.25, spoiled_below:30}`.
- Độ tươi lưu bằng `fractions.Fraction` (chính xác ở ngưỡng và floor). Đọc từ JSON được nắn về lưới 1/240 khi lệch dưới 1e-9 (tính theo đơn vị 1/240), nên giá trị ghi ra rồi đọc lại giữ đúng nhánh. Xuất JSON bằng `float`.
- Quán dùng một mô hình cá thể cho cả hai phiên bản; khi chưa bật v1.2, kho đếm được đổi thành cá thể độ tươi 100 không hao, đầu ra giữ nguyên từng byte.
- Code dùng chung đặt ở `chonoi/fresh.py` (hao, ngưỡng, đọc số) và `chonoi/inventory.py` (đọc/ghi/kiểm cả hai schema) để gather dùng lại.

## Hệ quả (bảng tác động)
| Module | File cần đổi | Test bị ảnh hưởng | Người phụ trách |
|---|---|---|---|
| Adapter / schema | `chonoi/fresh.py` (mới), `chonoi/inventory.py`, `chonoi/contract.py`, `chonoi/scenario.py` | thêm `tests/test_inventory_v12.py`; test cũ giữ nguyên | quangpham |
| Quán | `chonoi/sim/quan.py` | thêm `tests/test_quan_fresh.py`; test quán v1.1 giữ nguyên | quangpham |
| Lặn (gather) | `chonoi/sim/gather.py` (xem checklist) | `tests/test_gather_resources.py`, `tests/test_gather_rules.py`, `tests/test_python_starter_units.py` | lát gather (LongNhat2kruoi, KemmVSAI) — cần nhận |
| Contract | `game.contract.json`: `contract_version: "1.2"` + `freshness` trong cùng commit | mọi test hộp đen dùng fixture kho đếm (xem checklist) | Integrator, bật sau cùng |
| day / HUD | `play/main.py` (HUD đã đọc được cả hai schema), `chonoi/web/index.html` (cửa sổ thử) | kiểm bằng tay | lát 4 / HUD |

Thứ tự tích hợp để `main` luôn chạy: (1) adapter + quán sau cờ (không đổi hành vi hiện tại) → (2) gather sau cùng cờ → (3) bật v1.2 trong contract, đổi fixture, chạy regression P1–P2 → (4) gắn tag `phase-3`.

## Checklist khi bật v1.2 (những chỗ sẽ vỡ)
**Gather — `chonoi/sim/gather.py`**
- `self.hold = list(scenario.get("hold", []))`: giỏ phải là cá thể (scenario đã chuẩn hóa sẵn bằng `validate_item_list`, `fresh` là `Fraction`).
- Chỗ `hold.extend([kind] * qty)` khi hái/bắt: cấp cá thể mới `{"id": "I<n>", "kind", "fresh": 100}` bằng `IdAllocator` (họ `I`, tăng xuyên pha).
- Thêm bước hao 0.5/s (`fresh.per_tick(tuning, "gather")`), event `spoiled` với `location: "hold"`, `lost` là mảng cá thể theo LIFO.
- `inventory_items()` trả mảng cá thể (khi đó `runner.write_inventory` tự ghi schema mới); `gather_end.data.inventory` và snapshot `hold` xuất `fresh` bằng `fresh.to_json`. **`jsonl` không tự đổi `Fraction`, để lọt `Fraction` vào snapshot/event sẽ lỗi `TypeError`.**

**Test hộp đen (đọc contract của repo, nên không giữ schema đếm được)**
- `tests/test_smoke_p1.py`: các fixture `hold` dạng chuỗi kind, kết quả `{"items": {...}}`, `stock` dạng dict. Riêng ca "giỏ quá sức chứa → mã 2" phải dựng lại bằng mảng cá thể, nếu không sẽ trả mã 2 vì sai schema chứ không phải vì quá sức chứa.
- Test quán `tests/test_quan_customers.py`, `test_quan_fixture.py`, `test_quan_service.py`, `test_quan_v11.py`, `test_quan_data_v11.py`: đổi `stock`/`reserved` sang mảng cá thể/mảng id theo CHANGELOG, hoặc chuyển sang chạy trong tiến trình với tuning cũ. Không xóa test; ghi lý do trong commit.
- `tests/test_inventory_v12.py`, `tests/test_quan_fresh.py` dùng tuning v1.2 riêng, không phải sửa.

**Giao diện**
- `chonoi/web/index.html`: phần vẽ `snap.hold` và `snap.stock` đang coi là chuỗi kind / object đếm; cần gom theo `.kind` và hiện độ tươi.
- `play/main.py`: chỗ chuyển `inventory_items()` của gather sang `Session("quan", …)`; nếu gather còn trả dict thì quán báo lỗi mã 2.

**Sau khi bật**: chạy lại regression P1–P2. Tiền và điểm sẽ đổi theo thiết kế, vì giá chốt theo độ tươi.
