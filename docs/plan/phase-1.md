# Kế hoạch Phase 1

## Mục tiêu

Hoàn thành gameplay lõi của PRD-0, giữ Test Contract v1.0 chạy được và có bằng chứng kiểm chứng trong repo.

## Phân công và phụ thuộc

| Lát | Owner | Phụ thuộc | Đầu ra |
|---|---|---|---|
| Gather survival | LongNhat2kruoi | contract gather | bơi, oxy, ngạt, máu, faint, giỏ |
| Gather resources | KemmVSAI | gather survival, inventory | hái, bắt cá, regrow, cập bến, inventory |
| Quán gameplay | quangpham | contract quan, inventory | khách, giữ chỗ, bếp, phục vụ, tiền, uy tín |
| UI/QA/Release | buiductuan | snapshot/event contract | browser UI, test/e2e, bằng chứng, release |

## Tiêu chí hoàn thành

- Test contract và unit test chạy xanh bằng một lệnh.
- `gather` và `quan` độc lập trao đổi được inventory.
- Extension `day` chuyển từ gather sang quan trong cùng session.
- Cùng seed và input tạo JSONL giống byte.
- Có ma trận truy vết và bằng chứng chạy thật.

## Rủi ro

- Contract v1.2 kho cá thể chưa bật vì gather chưa hoàn thành migration; giữ v1.0/v1.1 chạy ổn định.
- `TEAM.md` và lịch sử commit phải khớp handle thật trên GitHub.
- UI sáng tạo không được làm thay đổi headless output.
