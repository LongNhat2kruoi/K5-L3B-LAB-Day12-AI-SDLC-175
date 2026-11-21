# Day 12 — AI SDLC: Quán Ăn Chợ Nổi

> **Làm theo nhóm 4–6 người** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)** (cần đăng nhập claude.ai; có trợ giảng AI cho từng phase).

## Chơi thử ngay (bản của nhóm)

**[▶ Chơi trên trình duyệt](https://raw.githack.com/LongNhat2kruoi/K5-L3B-LAB-Day12-AI-SDLC-175/main/play/index.html)**: luôn chạy code mới nhất ở `main`, không cần cài gì.

1. Lần đầu hiện trang "External Content Notice": bấm tiếp tục.
2. Bấm "Click to start" (chưa vào thì bấm thêm lần nữa), chờ khoảng 10 giây để tải.
3. W/S chọn, Enter xác nhận. Sáng: WASD bơi, E hái, Space bắt cá. Tối: WASD đi, E nấu/bưng/phục vụ. H mở hướng dẫn, Esc tạm dừng.

Chạy trên máy: `python -m http.server 8000` ở thư mục gốc repo rồi mở http://localhost:8000/play/

## Bắt buộc (chỉ có thế)

Cách làm việc kỹ thuật là **tự do** (push thẳng, nhánh + PR, pair, có hay không CI…). Cái bắt buộc:

1. **Một repo chung:** trưởng nhóm **fork** repo này, đặt tên `K5-L3B-LAB-Day12-AI-SDLC-<ten-nhom>`, thêm mọi thành viên làm collaborator (*Settings → Collaborators*, quyền Write) và để repo **public** (giảng viên xem được, không cần mời).
2. **Cả nhóm cùng commit** bằng tài khoản GitHub của mình, mỗi người **≥ 3 commit có nội dung** (làm cặp thì ghi `Co-authored-by:`).
3. **Điền [`TEAM.md`](TEAM.md):** danh sách thành viên + thỏa thuận làm việc nhóm; sửa `team_size` trong [`game.contract.json`](game.contract.json). Commit của người không có trong `TEAM.md` không được tính.
4. **Gắn tag** `phase-1` … `phase-4` đúng hạn; chạy được tại từng tag.
5. **Ghi chép tối thiểu:** `docs/verification/phase-n.md`, `docs/clarify.md`, `docs/ai-usage-log.md`, `docs/retro.md`, `docs/members/<handle>.md`.

## Bắt đầu nhanh

```bash
git clone <fork-của-nhóm> && cd <fork-của-nhóm>
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v        # smoke test
python3 -m chonoi.live --mode day                                    # chơi liền buổi sáng → buổi tối
```

Game cần chế độ **headless** theo Test Contract (`python3 -m chonoi.headless --mode gather|quan|day …`) để được chạy và chấm tự động. Bản `day` là extension chạy liền hai phase trong một session. **Công nghệ không ràng buộc**: khung Python trong `chonoi/` chỉ là gợi ý, chi tiết ở [`docs/STARTER.md`](docs/STARTER.md).

## Tự do sáng tạo

Ngoài phần đề yêu cầu, nhóm được **thêm** nhân vật, loài cá/cây, sinh vật, món, bản đồ, cơ chế, câu chuyện, đồ họa, âm nhạc… với ba điều kiện: **không phá phần cố định** (tắt ở headless), ghi mục **"Sáng tạo của nhóm"** trong README của nhóm, và **làm lõi đúng trước**.

### Sáng tạo của nhóm

- Bản chơi trình duyệt `play/` có sprite pixel-art Út Sen, HUD, menu, pause và vòng chơi liên tục.
- Extension `day` chuyển từ buổi sáng sang buổi tối trong cùng một session.
- Asset và giấy phép được liệt kê trong [`CREDITS.md`](CREDITS.md); bằng chứng day ở [`docs/proof/day-mode.md`](docs/proof/day-mode.md).

### Phase 4 / Release v1.0.0

Contract hiện tại là v1.3: gameplay, tuning, kho và JSONL dùng schema v1.2; Phase 4 bổ sung benchmark, soak và leaderboard.

```bash
python3 -m chonoi.benchmark --seed 42 --duration 30 --out bench.json
python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
python3 -m chonoi.headless --mode day --seed 42 --ticks 21602 --days 5 --leaderboard leaderboard.json --player-name "Út Sen" --out day.jsonl
python3 -m chonoi.headless --export-leaderboard leaderboard.json --leaderboard leaderboard.json
```

Ba cảnh báo UI có chữ/icon: thủy quái gần, oxy sắp hết và khách sắp giận. Bấm `C` hoặc nút “Tương phản cao” để bật chế độ dễ đọc. Bằng chứng Phase 4 ở [`docs/verification/phase-4.md`](docs/verification/phase-4.md).

## Lịch 3 giờ

| Mốc | Phase | Hạn tag |
|---|---|---|
| 0:00 | Phase 1 (PRD-0) | `phase-1` trước 1:00 |
| 1:00 | Phase 2 | `phase-2` trước 1:55 |
| 1:55 | Phase 3 | `phase-3` trước 2:30 |
| 2:30 | Phase 4 | `phase-4` + Release `v1.0.0` trước 3:00 |

Hết giờ mỗi phase thì gắn tag rồi đi tiếp; chỗ chưa xong ghi trung thực trong bằng chứng.

## Đánh giá (100 điểm)

| Hạng mục | Điểm |
|---|---|
| Test tự động ẩn (headless, gồm kiểm tra lại phase trước) | 25 |
| Làm việc nhóm (một repo chung, chia việc, tích hợp, đổi yêu cầu) | 25 |
| Kiểm chứng & bằng chứng | 15 |
| Harness AI (AGENTS.md, skill, nhật ký dùng AI) | 10 |
| Đánh giá & retro | 10 |
| Chất lượng sản phẩm (đúng yêu cầu, mở rộng/sáng tạo) | 10 |
| Demo | 5 |

## Quy định

- Dùng AI thoải mái; **không sao chép repo của nhóm khác**; bằng chứng phải thật.
- Nhân vật, bối cảnh là bản gốc của lab; asset ngoài chỉ dùng CC0/CC-BY/MIT hoặc tự tạo, ghi nguồn trong `CREDITS.md`. Không commit API key, token, `.env`.
