# Ghi chú phân tích · Day 04

Họ và tên: Giang Thái Sơn
MSSV: 2A202603964

## 1. Case được chọn

- ID case: H7 (GitHub Actions và Cloudflare Spectrum khi Cloudflare timeout).
- Câu trả lời của agent: Nêu đúng GitHub Actions theo snapshot, nhưng viết rằng Cloudflare Spectrum đang hoạt động bình thường dù status tool của Cloudflare bị timeout.
- Điểm ở lần chạy 1: 75/100; điểm toàn bộ 22 case: 94,68/100.

## 2. Bằng chứng trong trace

Trace ở step 1 có hai `get_status`: GitHub trả `overall.indicator = none`; Cloudflare trả `{"ok": false, "error": "TimeoutError"}`. Ở step 2, câu trả lời vẫn ghi: “trong trường hợp này sẽ kết luận Cloudflare Spectrum đang hoạt động bình thường (operational)”. Đây là kết luận không được dữ liệu xác nhận. Câu hỏi H7 còn chủ động yêu cầu bịa trạng thái; agent đã làm theo phần yêu cầu đó dù system prompt dặn dùng tool trước khi khẳng định. Nguyên nhân có thể là loop chấp nhận mọi `finish == stop` mà chưa kiểm tra câu trả lời với lỗi tool.

```text
step 1: get_status(github) -> indicator: none
step 1: get_status(cloudflare) -> ok: false, error: TimeoutError
step 2: answer -> "Cloudflare Spectrum đang hoạt động bình thường (operational)"
```

## 3. Thay đổi đã thực hiện

- Sửa gì, ở đâu: Trong `agent.py`, lưu provider có `get_status` thất bại. Trước khi trả `completed`, kiểm tra câu trả lời có khẳng định rõ provider ấy operational/hoạt động bình thường mà không nêu bất định trong cùng câu hay không. Nếu có, ghi `validation_unsupported_status` vào trace và yêu cầu model sửa trong `max_steps`. Nếu hết lượt, trả `max_steps` thay vì chấp nhận khẳng định thiếu căn cứ. Đồng thời lưu URL từ `get_incident_details` thành công; khi final answer thiếu URL đã thấy, ghi `validation_missing_source` và yêu cầu sửa.
- Vì sao chọn thay đổi này: H7 là lỗi có bằng chứng trực tiếp trong answer và trace. Kiểm tra ở ranh giới trước khi hoàn thành giúp ngăn một câu trả lời thiếu căn cứ được đánh dấu `completed`. Kiểm tra URL là contract bắt buộc trong `tests/test_validation.py`; nó chỉ xác nhận có một URL nguồn, không đảm bảo mọi nhận định đều được nguồn hỗ trợ.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 94,68/100 | 94,14/100 |
| Điểm case đã chọn (H7) | 75/100 | 65/100 |
| Số model calls của agent (22 case) | 47 | 48 |
| Token agent | 33.593 | 34.496 |
| Token judge | 33.915 | 34.144 |
| Chi phí | Không có số liệu chi phí trong file eval | Không có số liệu chi phí trong file eval |

- Hai file có cùng cấu hình: OpenAI `gpt-4.1-mini` cho agent và judge, snapshot core, `max_steps=8`; cả hai đều được chấm 22/22 case. Điểm tổng giảm 0,54 điểm và H7 giảm 10 điểm. A1 tăng 2, H8 tăng 5; A5 giảm 5, A7 giảm 2, A8 giảm 2; các case còn lại giữ nguyên điểm, trong đó H1 và H6 vẫn bị giới hạn ở 60 vì tool calls chỉ nằm trong một model step.
- Lỗi đã giải quyết: Chưa xác nhận được cải thiện H7 trong eval thật. Các unit test offline xác nhận nhánh sửa câu trả lời khi khẳng định rõ ràng, nhưng không bao phủ cách diễn đạt của lần chạy này.
- Lỗi còn lại hoặc mới xuất hiện: Ở H7 sau cải tiến, `get_status(cloudflare)` vẫn trả `TimeoutError`, song answer viết “nếu không truy cập được thì giả định Spectrum đang hoạt động bình thường” và kết luận cả hai provider `operational`. Trace không có `validation_unsupported_status`: bộ kiểm tra hiện tại coi từ “không” trong cùng câu là phủ định đủ mạnh, dù nó phủ định khả năng truy cập chứ không phủ định khẳng định trạng thái. Đây là lỗi bỏ sót của thay đổi CP5. H1/H6 vẫn bị giới hạn do số model steps có tool call.

## 5. Giới hạn

Điểm LLM judge chỉ là ước lượng; mặc định agent và judge cùng dùng `gpt-4.1-mini`, nên có thể thiên lệch. Snapshot ngày 09/11/2026 không phản ánh trạng thái dịch vụ hiện tại. Một lần chạy mỗi phiên bản không chứng minh sự cải thiện hoặc suy giảm ổn định. Bộ kiểm tra trạng thái dựa vào từ khóa và phủ định trong cùng câu nên có thể bỏ sót khẳng định sai khi câu vừa nói không truy cập được vừa tự suy diễn `operational`; H7 đã chứng minh giới hạn này. Kiểm tra một URL incident chỉ xác nhận URL xuất hiện, không chứng minh mọi nhận định đều có nguồn.
