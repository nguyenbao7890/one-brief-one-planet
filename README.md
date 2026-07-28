# One Brief, One Planet

Pipeline Python nhỏ để bản địa hóa creative F&B theo văn hóa từng thị trường.
Input là một brief gốc; output là image prompt tiếng Anh có thêm các quy tắc
`avoid` và `embrace` của thị trường mục tiêu.

## MVP hiện tại

- Đọc rule theo market từ `cultural_rules/*.json`.
- Validate các field quan trọng trước khi dùng.
- Preview prompt offline, không cần API key.
- Gọi Gemini qua một module trung gian duy nhất.
- Trả về kết quả có cấu trúc gồm prompt, rule và nguồn tham khảo.
- Mỗi rule có schema version, ngày review và trạng thái review.
- Có HTTP API `/health` và `/localize` để n8n gọi pipeline.
- Có test cho loader, validation và prompt assembly.

## Chạy local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Preview offline:

```bash
python3 prompt_rewriter.py \
  --brief "Chai trà thảo mộc mát lạnh, phong cách hiện đại" \
  --market japan \
  --preview
```

Gọi Gemini thật (sau khi điền `GEMINI_API_KEY` trong `.env`):

```bash
python3 prompt_rewriter.py \
  --brief "Chai trà thảo mộc mát lạnh, phong cách hiện đại" \
  --market middle_east_gulf
```

Output thật là JSON, ví dụ có các field `localized_prompt`, `applied_rules`,
`avoid_rules` và `sources`. Nhờ vậy n8n hoặc frontend có thể dùng trực tiếp
mà không cần tách thông tin ra khỏi một đoạn text tự do.

Các market đang có: `japan`, `middle_east_gulf`.

Chạy test:

```bash
python3 -m unittest discover -s tests -v
```

## Chạy HTTP API

```bash
python3 api_server.py --host 127.0.0.1 --port 8000
```

Kiểm tra service:

```bash
curl http://127.0.0.1:8000/health
```

Gửi brief tới pipeline:

```bash
curl -X POST http://127.0.0.1:8000/localize \
  -H 'Content-Type: application/json' \
  -d '{"brief":"Chai trà thảo mộc mát lạnh","market_id":"japan"}'
```

## Cấu trúc

```text
cultural_rules/       dữ liệu văn hóa, tách khỏi code
rule_loader.py        đọc và validate rule
prompt_rewriter.py    dựng prompt và CLI
api_server.py         HTTP adapter cho n8n
llm_client.py         boundary duy nhất với Gemini
tests/                test không cần gọi mạng
```

## Thêm một market mới

Tạo `cultural_rules/<market_id>.json` theo cấu trúc của file hiện có. Tối thiểu
cần `schema_version`, `market_id`, `market_name`, `avoid`, `embrace`, `sources`,
`last_reviewed` và `review_status`; sau đó chạy test
và thử `--preview`. `sources` là nơi lưu dấu vết nghiên cứu, không phải bằng
chứng rằng mọi rule đều đúng trong mọi hoàn cảnh. Trước khi dùng cho campaign
thật, rule nên được người bản địa hoặc chuyên gia thị trường review.

## Giới hạn đã biết và bước tiếp theo

Prototype hiện chỉ tạo text prompt; chưa có web UI, database, versioning rule
theo thời gian hay human approval workflow. Thứ tự mở rộng hợp lý là:

1. Thêm adapter HTTP nhỏ cho n8n.
2. Thêm human review trước khi xuất bản creative.
3. Thêm logging và bộ case đánh giá chất lượng theo market.
