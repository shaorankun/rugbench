ĐIỂM TỐT
Tiếp thu đầy đủ nhận xét đề cương và ghi rõ trong mục thay đổi: Cửa sổ quan sát trước lần rút thanh khoản cho SolRPDS, xử lý 6 nhóm clone mang cả hai nhãn, chọn độ đo theo từng bộ dữ liệu, kiểm định theo từng bộ, cấu hình cùng 10.000 dòng cho TabPFN, chuyển sang Vyper/Ape.
Phần blockchain có vai trò thật: RugRiskRegistry.vy lưu điểm rủi ro, hash đặc trưng và mã mô hình; GuardedPool.vy đọc điểm trong cùng giao dịch trước khi swap hoặc thêm thanh khoản; có kịch bản mô phỏng rug pull.
Chỉ số SDI (F1 trên toàn bộ dữ liệu trừ F1 trong cùng thế hệ trình biên dịch) là cách đo rõ ràng cho phát hiện về lối tắt; dataset card có số liệu thật và dòng mẫu thật.
Phần đánh giá nghiên cứu liên quan kỹ, chỉ ra được mâu thuẫn số liệu trong bài gốc.

CẦN HOÀN THIỆN CHO ĐỒ ÁN
Mức ưu tiên: Cao - Nên xử lý trước lần nộp tiếp theo · TB - Xử lý trong các tuần tới · Thấp - Chỉnh sửa trình bày.

Cao
Xác nhận sớm (trước tuần 5) bản phát hành SolRPDS có dữ liệu sự kiện theo từng pool hay không, vì cải tiến I2 phụ thuộc vào điều này. Nếu không có, chuyển sang phương án dự phòng đã nêu và ghi rõ trong báo cáo.
TBD1: Số cột đặc trưng và ý nghĩa các cột W1, Q1-Q4 chưa được xác nhận; nên đọc mã nguồn của tác giả hoặc liên hệ tác giả.
TB
Ngưỡng cảnh báo 7.000 trong registry nên được chọn từ tập validation (ghi precision/recall tại ngưỡng đó). Thảo luận rủi ro reporter ghi sai hoặc bị lộ khóa, và cân nhắc thời hạn hiệu lực của điểm rủi ro.

HƯỚNG MỞ RỘNG SAU MÔN HỌC (THAM KHẢO, KHÔNG BẮT BUỘC)
Kết quả về lối tắt trình biên dịch (F1 ≈ 0,95 chỉ với đặc trưng thế hệ trình biên dịch) đáng được phân tích sâu thành một nghiên cứu riêng về độ tin cậy của các bộ dữ liệu rug pull.
Thử chuyển giao chéo giữa các bộ dữ liệu và các chuỗi (huấn luyện trên một bộ, kiểm tra trên bộ khác có đặc trưng tương thích).
Thêm một mô hình dựa trên chuỗi opcode hoặc đồ thị để so sánh với các mô hình dạng bảng; công bố pipeline và giao thức đánh giá mở.
Phần này chỉ gợi ý cho nhóm muốn phát triển đề tài sau khi kết thúc môn học (nghiên cứu khoa học sinh viên, khóa luận). Không thuộc yêu cầu đồ án và không tính vào điểm.

LƯU Ý CHUNG CHO TẤT CẢ CÁC NHÓM
Giai đoạn này tập trung vào nội dung và phương pháp. Hình thức trình bày (bìa, mẫu báo cáo, chính tả, chú thích) sẽ hoàn thiện khi viết báo cáo cuối kỳ.
Phân tích và thí nghiệm dựa trên dữ liệu thật mà nhóm đã tải; nếu dùng dữ liệu mô phỏng, ghi rõ cách sinh, tham số và seed.
Nêu rõ Blockchain đảm bảo điều gì (toàn vẹn, không phát hành trùng, lưu vết) và không đảm bảo điều gì (dữ liệu đầu vào đúng, mô hình đúng); ai đưa dữ liệu lên chuỗi và rủi ro nếu bên đó khai sai hoặc lộ khóa.
Ghi lại các thay đổi so với đề cương (dữ liệu, công cụ, phương pháp) và lý do, để dễ tổng hợp khi viết báo cáo.
Smart contract dùng Vyper + Ape theo môn học; nhóm nào cần dùng công cụ khác nên trao đổi trước khi chuyển.
Nghiên cứu liên quan ưu tiên bài đã bình duyệt, có DOI hoặc link kiểm chứng được.
Mỗi cải tiến có baseline cụ thể và độ đo; baseline nên là cách làm hợp lý mà người khác có thể chọn, không phải phương án cố tình yếu.