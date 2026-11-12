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

- Sửa gì, ở đâu: Trong `agent.py`, lưu provider có `get_status` thất bại. Trước khi trả `completed`, kiểm tra câu trả lời có khẳng định provider ấy operational/hoạt động bình thường mà không phủ định trực tiếp nhận định trạng thái hay không. Sau lần eval đầu tiên bỏ sót câu “không truy cập được nhưng giả định operational”, mình thu hẹp cách nhận diện phủ định và bổ sung chỉ dẫn hệ thống. Nếu phát hiện khẳng định sai, ghi `validation_unsupported_status` vào trace và yêu cầu model sửa trong `max_steps`; hết lượt thì trả `max_steps`. Đồng thời lưu URL từ `get_incident_details` thành công; khi final answer thiếu URL đã thấy, ghi `validation_missing_source` và yêu cầu sửa.
- Vì sao chọn thay đổi này: H7 là lỗi có bằng chứng trực tiếp trong answer và trace. Kiểm tra ở ranh giới trước khi hoàn thành giúp ngăn một câu trả lời thiếu căn cứ được đánh dấu `completed`. Kiểm tra URL là contract bắt buộc trong `tests/test_validation.py`; nó chỉ xác nhận có một URL nguồn, không đảm bảo mọi nhận định đều được nguồn hỗ trợ.

## 4. So sánh hai lần chạy

| Chỉ số | `eval_before.json` | `eval_after.json` |
|---|---|---|
| Điểm tổng | 94,68/100 | 92,82/100 |
| Điểm case đã chọn (H7) | 75/100 | 96/100 |
| Số model calls của agent (22 case) | 47 | 50 |
| Token agent | 33.593 | 40.467 |
| Token judge | 33.915 | 33.391 |
| Chi phí | Không có số liệu chi phí trong file eval | Không có số liệu chi phí trong file eval |

- Hai file có cùng cấu hình: OpenAI `gpt-4.1-mini` cho agent và judge, snapshot core, `max_steps=8`; cả hai đều được chấm 22/22 case. Điểm tổng giảm 1,86 điểm dù H7 tăng 21 điểm. E5 giảm 2, A1 tăng 2, A5 giảm 5, H2 giảm 50, H8 giảm 7; các case khác giữ nguyên điểm.
- Lỗi đã giải quyết: H7 sau cải tiến có `get_status(cloudflare) -> TimeoutError`, rồi event `validation_unsupported_status` và một model call sửa câu trả lời. Answer cuối nói Cloudflare Spectrum “chưa xác minh được” thay vì bịa operational; điểm H7 tăng từ 75 lên 96. Unit test offline gồm cả câu sai của lần eval trước; toàn bộ 41 test pass.
- Lỗi còn lại hoặc mới xuất hiện: H2 chỉ gọi `get_incident_details`, thiếu `get_status` theo yêu cầu case nên bị áp trần 50 điểm; câu trả lời vẫn nói về trạng thái hiện tại mà chưa kiểm tra status trực tiếp. H8 giảm 7 điểm do judge đánh giá thiếu chi tiết. H1 và H6 vẫn bị áp trần 60 vì tool calls chỉ ở một model step. Các biến động khác có thể do lần chạy model/judge, không đủ bằng chứng kết luận thay đổi code là nguyên nhân.

## 5. Giới hạn

Điểm LLM judge chỉ là ước lượng; agent và judge cùng dùng `gpt-4.1-mini`, nên có thể thiên lệch. Snapshot ngày 09/11/2026 không phản ánh trạng thái dịch vụ hiện tại. Một lần chạy mỗi phiên bản không chứng minh sự cải thiện hoặc suy giảm ổn định; điểm tổng sau thấp hơn dù H7 đã đúng. Bộ kiểm tra trạng thái vẫn dựa trên từ khóa và cách phủ định, có thể bỏ sót cách diễn đạt khác hoặc yêu cầu thêm model call. Kiểm tra một URL incident chỉ xác nhận URL xuất hiện, không chứng minh mọi nhận định đều có nguồn; H6 còn dẫn một URL incident gộp sai ký tự dù có URL của incident đã quan sát.
