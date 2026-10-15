# -*- coding: utf-8 -*-
"""
fetch_news.py - Gom tin cho 3 tab của app, ghi ra data/tin.json
  Tab 1: Tin nhanh Nha Trang (7 mục, có dự báo thời tiết)
  Tab 2: Chứng khoán - mục Tin tức (5 nhóm ngành)
  Tab 3: Công nghệ (Xe ô tô - loại trừ xe Trung Quốc; Công nghệ AI)

Chạy: python fetch_news.py
Chỉ dùng nguồn KHÔNG cần đăng nhập, KHÔNG cần API key:
  - RSS của ~35 báo chính thống (VnExpress, Tuổi Trẻ, Thanh Niên, Dân trí, VietNamNet, Tiền Phong, Znews, CafeF,
    Vietnam+, Báo Chính phủ, Nhân Dân, VOV, VTV, Báo Khánh Hòa...) - bot tự dò link kênh RSS từ trang RSS của từng báo
  - Bing News RSS (có đoạn tóm tắt) và Google News RSS (phủ gần như mọi báo, kể cả báo không có RSS) - chỉ nhận báo chính thống
  - Open-Meteo (dự báo thời tiết Nha Trang)
Nguyên tắc: không bịa nội dung. Tóm tắt lấy từ chính nguồn tin (RSS hoặc thẻ mô tả của bài gốc).
Chỉ dùng thư viện chuẩn của Python, không cần cài thêm.
"""
import base64
import html
import json
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote, urlparse, parse_qs, urljoin, unquote

THU_MUC = Path(__file__).parent / "data"
THU_MUC.mkdir(exist_ok=True)
VN = timezone(timedelta(hours=7))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"

SO_TIN_MOI_MUC = 15     # mỗi mục giữ tối đa bao nhiêu tin (app hiện 3, bấm "Xem thêm" ra phần còn lại)
DO_DAI_TOM_TAT = 280    # cắt tóm tắt cho gọn
NGUONG_TRUNG = 0.65     # 2 tiêu đề giống nhau >= 65% số từ -> coi là cùng 1 tin (trùng lặp)

# ===================== CẤU HÌNH NỘI DUNG (sửa ở đây khi muốn đổi) =====================
# Mỗi mục: key, tên hiển thị, câu tìm kiếm (Bing/Google), từ khóa nhận diện, từ khóa loại trừ.
# Từ khóa là biểu thức chính quy, không phân biệt hoa/thường.
DIA_PHUONG = r"nha trang|khánh hòa|khánh hoà|cam ranh|ninh hòa|ninh hoà|vạn ninh|diên khánh|cam lâm|khánh vĩnh|khánh sơn|vịnh nha trang|hòn tre|trường sa"

XE_TRUNG_QUOC = (r"\bbyd\b|chery|omoda|jaecoo|geely|\bmg\s?\d|\bmg\b|wuling|haval|\bgwm\b|great wall|\btank\s?\d|"
                 r"\bora\b|lynk|zeekr|xpeng|\bnio\b|li auto|xiaomi|\bsu7\b|\byu7\b|\baito\b|seres|changan|deepal|avatr|"
                 r"hongqi|dongfeng|voyah|\bbaic\b|jetour|exeed|\bgac\b|\baion\b|hyptec|leapmotor|skyworth|\bjac\b|"
                 r"haima|kaiyi|saic|baojun|trumpchi|soueast|forthing|denza|fangchengbao|yangwang|\bjmc\b|"
                 r"trung quốc|tàu|china|chinese")

TAB = {
    "nha_trang": {
        "ten": "Tin nhanh Nha Trang",
        "so_ngay": 30,
        "bat_buoc": DIA_PHUONG,
        "rss": [
            "https://vnexpress.net/rss/thoi-su.rss", "https://vnexpress.net/rss/bat-dong-san.rss",
            "https://vnexpress.net/rss/du-lich.rss", "https://vnexpress.net/rss/giao-duc.rss",
            "https://vnexpress.net/rss/phap-luat.rss", "https://vnexpress.net/rss/kinh-doanh.rss",
            "https://vnexpress.net/rss/tin-moi-nhat.rss",
            "https://tuoitre.vn/rss/thoi-su.rss", "https://thanhnien.vn/rss/thoi-su.rss",
        ],
        "muc": [
            {"key": "ha_tang", "ten": "Hạ tầng giao thông",
             "tim": ["Nha Trang hạ tầng giao thông", "Khánh Hòa cao tốc", "Khánh Hòa dự án đường giao thông",
                     "sân bay Cam Ranh", "Nha Trang nút giao cầu đường"],
             "tu_khoa": r"cao tốc|quốc lộ|tuyến đường|nút giao|cầu |hầm|sân bay|đường sắt|ga |cảng|hạ tầng|giao thông|"
                        r"mở rộng đường|nâng cấp đường|thông xe|khởi công|đường ven biển|đèo|bến xe|đường bộ",
             "loai_tru": r"tai nạn|tông|va chạm|tử vong|bắt giữ|khởi tố"},
            {"key": "quy_hoach", "ten": "Quy hoạch đô thị – Bất động sản & dự án",
             "tim": ["Nha Trang quy hoạch đô thị", "Khánh Hòa bất động sản", "Nha Trang dự án khu đô thị",
                     "Khánh Hòa đấu giá đất", "Nha Trang nhà ở xã hội"],
             "tu_khoa": r"quy hoạch|bất động sản|khu đô thị|dự án|nhà ở|căn hộ|chung cư|đất|đấu giá|condotel|"
                        r"giải phóng mặt bằng|tái định cư|chỉnh trang|đô thị|nhà đầu tư|giá nhà",
             "loai_tru": r"tai nạn|bắt giữ"},
            {"key": "kinh_te_vh", "ten": "Môi trường kinh tế – văn hóa",
             "tim": ["Khánh Hòa kinh tế tăng trưởng", "Khánh Hòa thu hút đầu tư", "Nha Trang văn hóa lễ hội",
                     "Khánh Hòa doanh nghiệp xuất khẩu"],
             "tu_khoa": r"kinh tế|tăng trưởng|grdp|ngân sách|đầu tư|doanh nghiệp|xuất khẩu|sản xuất|thương mại|"
                        r"văn hóa|lễ hội|di sản|nghệ thuật|tháp bà|festival|triển lãm|bảo tàng|biểu diễn|khu công nghiệp",
             "loai_tru": r"tai nạn"},
            {"key": "du_lich", "ten": "Thị trường du lịch – dịch vụ",
             "tim": ["Nha Trang du lịch", "Khánh Hòa du khách quốc tế", "Nha Trang khách sạn resort",
                     "Nha Trang dịch vụ du lịch"],
             "tu_khoa": r"du lịch|du khách|khách quốc tế|lượt khách|khách sạn|resort|nhà hàng|tour|lữ hành|"
                        r"bãi biển|homestay|vinpearl|đảo|lặn biển|ẩm thực|chuyến bay|hãng bay|tàu biển|dịch vụ",
             "loai_tru": r"tai nạn|chết đuối|đuối nước"},
            {"key": "giao_duc", "ten": "Giáo dục",
             "tim": ["Khánh Hòa giáo dục", "Nha Trang trường học học sinh", "Đại học Nha Trang", "Khánh Hòa tuyển sinh"],
             "tu_khoa": r"giáo dục|trường|học sinh|sinh viên|giáo viên|tuyển sinh|đại học|thi |kỳ thi|học bổng|"
                        r"lớp học|mầm non|học phí|sở gd",
             "loai_tru": r""},
            {"key": "phap_luat", "ten": "Pháp luật",
             "tim": ["Khánh Hòa khởi tố", "Nha Trang công an bắt", "Khánh Hòa xử phạt vi phạm", "Nha Trang lừa đảo"],
             "tu_khoa": r"khởi tố|bắt |bắt giữ|tạm giam|công an|xử phạt|phạt|lừa đảo|vi phạm|điều tra|xét xử|tòa|"
                        r"án |ma túy|trộm|cướp|tai nạn|kỷ luật|truy nã|đánh bạc|buôn lậu",
             "loai_tru": r""},
            {"key": "thoi_tiet", "ten": "Dự báo thời tiết",
             "tim": ["thời tiết Khánh Hòa", "Nha Trang mưa bão", "Khánh Hòa áp thấp nhiệt đới", "Khánh Hòa ngập lụt"],
             "tu_khoa": r"thời tiết|mưa|bão|áp thấp|lũ|ngập|nắng nóng|triều cường|sạt lở|gió mùa|không khí lạnh|"
                        r"dự báo|biển động|sóng lớn|thiên tai",
             "loai_tru": r""},
        ],
    },
    "chung_khoan": {
        "ten": "Chứng khoán – Tin tức",
        "so_ngay": 14,
        "bat_buoc": "",
        "rss": [
            "https://cafef.vn/thi-truong-chung-khoan.rss", "https://cafef.vn/tai-chinh-ngan-hang.rss",
            "https://cafef.vn/doanh-nghiep.rss", "https://cafef.vn/vi-mo-dau-tu.rss",
            "https://cafef.vn/thi-truong.rss", "https://vnexpress.net/rss/kinh-doanh.rss",
        ],
        "muc": [
            {"key": "xay_dung", "ten": "Xây dựng – Đầu tư công",
             "tim": ["giải ngân đầu tư công", "cổ phiếu xây dựng đầu tư công", "Vinaconex VCG", "Coteccons CTD",
                     "Đèo Cả HHV", "FECON FCN", "Lizen LCG", "cao su GVR khu công nghiệp"],
             "tu_khoa": r"đầu tư công|giải ngân|cao tốc|hạ tầng|xây dựng|nhà thầu|vinaconex|\bvcg\b|coteccons|\bctd\b|"
                        r"đèo cả|\bhhv\b|fecon|\bfcn\b|lizen|\blcg\b|\bgvr\b|\bphr\b|cao su|khu công nghiệp|vật liệu xây dựng",
             "loai_tru": r""},
            {"key": "ngan_hang", "ten": "Ngân hàng",
             "tim": ["cổ phiếu ngân hàng", "lãi suất ngân hàng", "Vietcombank VCB", "VPBank VPB", "HDBank HDB",
                     "tín dụng ngân hàng nhà nước"],
             "tu_khoa": r"ngân hàng|tín dụng|lãi suất|nhnn|nợ xấu|vietcombank|\bvcb\b|vpbank|\bvpb\b|hdbank|\bhdb\b|"
                        r"huy động|cho vay|tỷ giá",
             "loai_tru": r""},
            {"key": "cntt", "ten": "Công nghệ thông tin",
             "tim": ["cổ phiếu công nghệ FPT", "CMC CMG", "Thế Giới Di Động MWG", "Digiworld DGW",
                     "doanh nghiệp công nghệ thông tin Việt Nam"],
             "tu_khoa": r"\bfpt\b|\bcmc\b|\bcmg\b|thế giới di động|\bmwg\b|digiworld|\bdgw\b|công nghệ|phần mềm|"
                        r"chuyển đổi số|bán dẫn|chip|trung tâm dữ liệu|viễn thông|bán lẻ",
             "loai_tru": r""},
            {"key": "thep", "ten": "Thép",
             "tim": ["cổ phiếu thép", "giá thép", "Hòa Phát HPG", "Hoa Sen HSG", "Nam Kim NKG", "chống bán phá giá thép"],
             "tu_khoa": r"thép|hòa phát|\bhpg\b|hoa sen|\bhsg\b|nam kim|\bnkg\b|quặng sắt|tôn |phôi|luyện kim|dung quất",
             "loai_tru": r""},
            {"key": "vang_bac", "ten": "Vàng bạc trang sức",
             "tim": ["giá vàng hôm nay", "PNJ cổ phiếu", "thị trường vàng", "giá bạc", "trang sức"],
             "tu_khoa": r"vàng|\bsjc\b|\bpnj\b|trang sức|kim cương|giá bạc|\bbạc\b|nhẫn trơn|đá quý",
             "loai_tru": r"vàng da|lá vàng|thời kỳ vàng|cơ hội vàng|giờ vàng|ngôi sao vàng|cờ vàng"},
        ],
    },
    "cong_nghe": {
        "ten": "Công nghệ",
        "so_ngay": 30,
        "bat_buoc": "",
        "rss": [
            "https://vnexpress.net/rss/oto-xe-may.rss", "https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss",
            "https://tuoitre.vn/rss/xe.rss", "https://tuoitre.vn/rss/nhip-song-so.rss",
            "https://thanhnien.vn/rss/xe.rss", "https://thanhnien.vn/rss/cong-nghe.rss",
            "https://dantri.com.vn/rss/o-to-xe-may.rss", "https://dantri.com.vn/rss/cong-nghe.rss",
        ],
        "muc": [
            {"key": "o_to", "ten": "Xe ô tô – dòng xe mới, thiết kế",
             "tim": ["ô tô mới ra mắt", "mẫu xe mới thiết kế", "xe thế hệ mới ra mắt", "ô tô nâng cấp facelift",
                     "concept xe hơi", "nội thất ngoại thất xe mới", "Toyota Honda Hyundai Kia Mazda ra mắt",
                     "Mercedes BMW Audi Porsche mẫu mới", "VinFast mẫu xe mới"],
             "tu_khoa": r"ra mắt|mẫu xe|thế hệ mới|thiết kế|nâng cấp|phiên bản|concept|trình làng|facelift|lộ diện|"
                        r"nội thất|ngoại thất|khung gầm|động cơ|hybrid|xe điện|suv|sedan|crossover|bán tải|"
                        r"\bô tô\b|\bxe hơi\b",
             # ngoài xe Trung Quốc còn loại xe máy và tin tai nạn/giao thông
             "loai_tru": XE_TRUNG_QUOC + r"|xe máy|xe tay ga|mô tô|môtô|xe số|xe đạp|tai nạn|phạt|csgt|"
                                         r"đăng kiểm|biển số|tài xế|vi phạm|bằng lái|giấy phép lái",
             "bat_buoc": r"ô tô|xe hơi|\bxe\b|suv|sedan|crossover|bán tải|minivan|hatchback|coupe|"
                         r"toyota|honda|hyundai|kia|mazda|ford|mitsubishi|nissan|suzuki|subaru|lexus|mercedes|bmw|audi|"
                         r"porsche|volkswagen|volvo|vinfast|tesla|peugeot|land rover|jeep|ferrari|lamborghini|bentley|"
                         r"rolls|mclaren|aston|genesis|isuzu|skoda|renault|cadillac|chevrolet"},
            {"key": "ai", "ten": "Công nghệ AI",
             "tim": ["trí tuệ nhân tạo", "công nghệ AI mới", "ChatGPT OpenAI", "Google Gemini AI",
                     "AI tạo sinh", "Nvidia chip AI", "ứng dụng AI Việt Nam"],
             "tu_khoa": r"trí tuệ nhân tạo|chatgpt|openai|gemini|claude|anthropic|copilot|\bllm\b|chatbot|"
                        r"học máy|machine learning|deepmind|nvidia|ai tạo sinh|mô hình ngôn ngữ|agent",
             "loai_tru": r""},
        ],
    },
}
# Mục lấy được nhưng không khớp mục nào sẽ bị bỏ. Một tin chỉ thuộc DUY NHẤT 1 mục (không trùng lặp giữa các mục).

# ===================== DANH SÁCH BÁO: BOT TỰ DÒ KÊNH RSS =====================
# (tên hiển thị, tên miền, [các trang liệt kê RSS - thử lần lượt, cuối cùng thử trang chủ], tab được cấp tin)
# Bot đọc trang liệt kê RSS để tìm link kênh THẬT => báo đổi đường dẫn RSS vẫn không hỏng.
# Các kênh chạy tốt được nhớ ở data/nguon_rss.json (lần sau dò hụt vẫn dùng lại).
# Muốn thêm báo: thêm 1 dòng. Báo không có RSS (vd Báo Khánh Hòa) vẫn lấy được qua Bing/Google (xem BAO_DIA_PHUONG).
NT, CK, CN = "nha_trang", "chung_khoan", "cong_nghe"
CA_BA = (NT, CK, CN)
BAO = {
    # --- báo tổng hợp quốc gia (cấp tin cho cả 3 tab, bot chỉ lấy các kênh liên quan) ---
    "vnexpress": ("VnExpress", "vnexpress.net", ["https://vnexpress.net/rss"], CA_BA),
    "tuoitre": ("Tuổi Trẻ", "tuoitre.vn", ["https://tuoitre.vn/rss.htm"], CA_BA),
    "thanhnien": ("Thanh Niên", "thanhnien.vn", ["https://thanhnien.vn/rss.html"], CA_BA),
    "dantri": ("Dân trí", "dantri.com.vn", ["https://dantri.com.vn/rss.htm", "https://dantri.com.vn/rss"], CA_BA),
    "vietnamnet": ("VietNamNet", "vietnamnet.vn", ["https://vietnamnet.vn/rss"], CA_BA),
    "tienphong": ("Tiền Phong", "tienphong.vn", ["https://tienphong.vn/rss/"], CA_BA),
    "znews": ("Znews", "znews.vn", ["https://znews.vn/rss.html", "https://znews.vn/rss"], CA_BA),
    "nld": ("Người Lao Động", "nld.com.vn", ["https://nld.com.vn/rss.htm", "https://nld.com.vn/rss.html"], CA_BA),
    "laodong": ("Lao Động", "laodong.vn", ["https://laodong.vn/rss"], CA_BA),
    "vov": ("VOV", "vov.vn", ["https://vov.vn/rss"], CA_BA),
    "vtv": ("VTV", "vtv.vn", ["https://vtv.vn/rss.htm", "https://vtv.vn/rss"], CA_BA),
    "vietnamplus": ("Vietnam+", "vietnamplus.vn", ["https://www.vietnamplus.vn/rss.html"], CA_BA),
    "baotintuc": ("Báo Tin tức (TTXVN)", "baotintuc.vn", ["https://baotintuc.vn/rss.html", "https://baotintuc.vn/rss"], CA_BA),
    "baochinhphu": ("Báo Chính phủ", "baochinhphu.vn", ["https://baochinhphu.vn/rss.htm", "https://baochinhphu.vn/rss"], CA_BA),
    "nhandan": ("Báo Nhân Dân", "nhandan.vn", ["https://nhandan.vn/rss", "https://nhandan.vn/rss.html"], CA_BA),
    "sggp": ("Sài Gòn Giải Phóng", "sggp.org.vn", ["https://www.sggp.org.vn/rss", "https://www.sggp.org.vn/rss.html"], (NT, CK)),
    "plo": ("Pháp Luật TP.HCM", "plo.vn", ["https://plo.vn/rss"], (NT, CK)),
    # --- chuyên địa phương Khánh Hòa ---
    "baokhanhhoa": ("Báo Khánh Hòa", "baokhanhhoa.vn", ["https://baokhanhhoa.vn/rss", "https://baokhanhhoa.vn/rss.html"], (NT,)),
    "khanhhoa_gov": ("Cổng TTĐT Khánh Hòa", "khanhhoa.gov.vn", ["https://khanhhoa.gov.vn/rss"], (NT,)),
    # --- tài chính, chứng khoán, doanh nghiệp ---
    "cafef": ("CafeF", "cafef.vn", ["https://cafef.vn/rss.chn", "https://cafef.vn/rss"], (CK,)),
    "cafebiz": ("CafeBiz", "cafebiz.vn", ["https://cafebiz.vn/rss.chn"], (CK,)),
    "vietstock": ("Vietstock", "vietstock.vn", ["https://vietstock.vn/rss"], (CK,)),
    "vneconomy": ("VnEconomy", "vneconomy.vn", ["https://vneconomy.vn/rss.html", "https://vneconomy.vn/rss"], (CK,)),
    "baodautu": ("Báo Đầu tư", "baodautu.vn", ["https://baodautu.vn/rss.htm", "https://baodautu.vn/rss"], (CK, NT)),
    "thesaigontimes": ("Kinh tế Sài Gòn", "thesaigontimes.vn", ["https://thesaigontimes.vn/rss"], (CK,)),
    "tinnhanhchungkhoan": ("Tin nhanh chứng khoán", "tinnhanhchungkhoan.vn", ["https://tinnhanhchungkhoan.vn/rss/"], (CK,)),
    "nhipcaudautu": ("Nhịp cầu đầu tư", "nhipcaudautu.vn", ["https://nhipcaudautu.vn/rss"], (CK,)),
    "baoxaydung": ("Báo Xây dựng", "baoxaydung.vn", ["https://baoxaydung.vn/rss"], (CK, NT)),
    "congthuong": ("Báo Công Thương", "congthuong.vn", ["https://congthuong.vn/rss"], (CK,)),
    "thoibaotaichinh": ("Thời báo Tài chính VN", "thoibaotaichinhvietnam.vn", ["https://thoibaotaichinhvietnam.vn/rss"], (CK,)),
    # --- công nghệ, ô tô ---
    "genk": ("GenK", "genk.vn", ["https://genk.vn/rss.chn"], (CN,)),
    "tinhte": ("Tinh tế", "tinhte.vn", ["https://tinhte.vn/rss"], (CN,)),
    "ictnews": ("ICTnews", "ictnews.vietnamnet.vn", ["https://ictnews.vietnamnet.vn/rss"], (CN, CK)),
    "vnreview": ("VnReview", "vnreview.vn", ["https://vnreview.vn/rss"], (CN,)),
    "autopro": ("Autopro", "autopro.com.vn", ["https://autopro.com.vn/rss.chn"], (CN,)),
}

# Báo/trang địa phương không có RSS: bot tìm bằng Bing/Google với "site:" (mỗi mục Nha Trang tìm thêm theo chủ đề).
BAO_DIA_PHUONG = ["baokhanhhoa.vn", "khanhhoa.gov.vn"]
CHU_DE_DIA_PHUONG = {"ha_tang": "giao thông", "quy_hoach": "quy hoạch dự án", "kinh_te_vh": "kinh tế văn hóa",
                     "du_lich": "du lịch", "giao_duc": "giáo dục", "phap_luat": "pháp luật", "thoi_tiet": "thời tiết mưa bão"}

# Chỉ nhận tin từ báo chính thống: các báo trong BAO, báo/tạp chí có tên miền bắt đầu bằng "bao"/"tapchi",
# cổng thông tin *.gov.vn / *.edu.vn và danh sách dưới đây. Tin từ nguồn lạ (blog, trang rác) bị loại,
# tên miền bị loại được liệt kê ở meta.nguon.mien_bi_loai trong data/tin.json để bạn bổ sung nếu cần.
CHI_BAO_CHINH_THONG = True
THEM_BAO_CHINH_THONG = [
    "zingnews.vn", "kenh14.vn", "soha.vn", "afamily.vn", "vnanet.vn", "dantocmiennui.vn", "bnews.vn", "bizhub.vn",
    "qdnd.vn", "cand.com.vn", "congan.com.vn", "hanoimoi.vn", "kinhtedothi.vn", "doanhnhansaigon.vn", "vietnamfinance.vn",
    "tapchicongsan.org.vn", "vtc.vn", "vtcnews.vn", "kienthuc.net.vn", "nguoiduatin.vn", "vietnamnews.vn",
    "thanhtra.com.vn", "giaoducthoidai.vn", "vov.gov.vn", "nhandan.org.vn", "vneconomy.vn", "ndh.vn", "tinnhanhchungkhoan.vn",
    "doisongphapluat.com", "baophapluat.vn", "vietnamdaily.vn", "toquoc.vn", "congly.vn", "phunuonline.com.vn",
    "tuoitrethudo.vn", "nongnghiepmoitruong.vn", "vietq.vn", "dienanhvietnam.vn", "tiepthigiadinh.vn", "motgoc.vn",
]
TOI_DA_KENH_MOI_BAO = 14   # mỗi báo, mỗi tab lấy tối đa bao nhiêu kênh RSS liên quan
TIM_KIEM_SONG_SONG = 6     # số luồng tìm kiếm Bing/Google (giữ thấp để không bị chặn)
KENH_SONG_SONG = 10        # số luồng đọc RSS các báo

# Kênh RSS nào "liên quan" tab nào (so khớp phần đường dẫn đã bỏ dấu, dạng chuyen-muc). Báo chỉ có <= 3 kênh thì lấy hết.
_T = r"(^|[-/_.])({})([-/_.]|$)"
SLUG_QUAN_TAM = {
    NT: _T.format("thoi-su|thoisu|xa-hoi|xahoi|dia-phuong|diaphuong|mien-trung|kinh-te|kinhte|kinh-doanh|kinhdoanh|bat-dong-san|"
                  "batdongsan|du-lich|dulich|giao-duc|giaoduc|phap-luat|phapluat|giao-thong|giaothong|moi-truong|moitruong|"
                  "van-hoa|vanhoa|doi-song|doisong|trong-nuoc|trongnuoc|home|trang-chu|tin-moi-nhat|tin-moi|tin-nong|"
                  "thoi-tiet|thoitiet|nong-nghiep|khanh-hoa|khanhhoa|nha-trang|nhatrang|doanh-nghiep|doanhnghiep"),
    CK: _T.format("kinh-te|kinhte|kinh-doanh|kinhdoanh|chung-khoan|chungkhoan|tai-chinh|taichinh|ngan-hang|nganhang|doanh-nghiep|"
                  "doanhnghiep|bat-dong-san|batdongsan|vi-mo|vimo|thi-truong|thitruong|tinthitruong|dau-tu|dautu|vang|xay-dung|"
                  "xaydung|cong-nghe|congnghe|thep|hang-hoa|home|trang-chu|tin-moi-nhat|tin-moi|thoi-su|thoisu|smart-money|"
                  "cong-nghiep|congnghiep|ha-tang|hatang"),
    CN: _T.format("cong-nghe|congnghe|so-hoa|sohoa|nhip-song-so|khoa-hoc|khoahoc|khoa-hoc-cong-nghe|oto|o-to|otoxemay|oto-xe-may|"
                  "xe|xe-co|xeco|ai|tri-tue-nhan-tao|may-tinh|dien-thoai|mobile|internet|thi-truong|thitruong|home|trang-chu|"
                  "tin-moi-nhat|tin-moi|thiet-bi|thietbi|kham-pha|khampha|san-pham-moi|sanphammoi"),
}


# ===================== HÀM TIỆN ÍCH =====================
HAN_CHOT = time.time() + 12 * 60   # sau 12 phút bot ngừng lấy thêm, ghi những gì đã có (workflow cho tối đa 20 phút)
_KHOA = threading.Lock()
GHI_KENH = {}                       # url kênh RSS -> số tin lấy được (-1 = lỗi)
NK = {"bing": [0, 0], "google": [0, 0], "mien_bi_loai": Counter()}   # nhật ký chẩn đoán ghi vào tin.json


def tai(url, timeout=15):
    if time.time() > HAN_CHOT:
        raise TimeoutError("hết thời gian chạy của bot")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "vi-VN,vi;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def lam_sach(s):
    """Bỏ thẻ HTML, giải mã ký tự, gộp khoảng trắng."""
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()


def chuan(s):
    """Chuẩn hoá để so khớp: thường, NFC, bỏ dấu câu."""
    s = unicodedata.normalize("NFC", (s or "").lower())
    return re.sub(r"[^\w\s]", " ", s)


def bo_dau(s):
    s = unicodedata.normalize("NFD", s)
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d").replace("Đ", "D")


def tu_cua(tieu_de):
    """Tập từ có nghĩa của tiêu đề (bỏ dấu để so được cả khi nguồn gõ dấu khác nhau)."""
    return {w for w in bo_dau(chuan(tieu_de)).split() if len(w) > 1}


def giong_nhau(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def co_tieng_viet(s):
    return bool(re.search(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]", (s or "").lower()))


def doc_ngay(chuoi):
    try:
        d = parsedate_to_datetime(chuoi)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(VN)
    except (TypeError, ValueError, IndexError):
        return None


def link_that(link):
    """Bing trả link dạng apiclick.aspx?url=... -> lấy link bài gốc."""
    try:
        u = urlparse(link)
        if "bing.com" in u.netloc and "apiclick" in u.path:
            return parse_qs(u.query).get("url", [link])[0]
    except ValueError:
        pass
    return link


def giai_ma_google(link):
    """Link Google News dạng /rss/articles/<mã>: mã kiểu cũ có chứa sẵn địa chỉ bài gốc -> lấy ra (để đọc tóm tắt từ bài gốc).
    Mã kiểu mới không giải được thì giữ nguyên link Google (bấm vào vẫn chuyển tới bài báo)."""
    m = re.search(r"/articles/([A-Za-z0-9_-]+)", link or "")
    if not m:
        return link
    try:
        s = m.group(1)
        raw = base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
        mm = re.search(rb"https?://[\x21-\x7e]+", raw)
        if mm:
            u = mm.group(0).decode("ascii", "ignore")
            if "google." not in urlparse(u).netloc:
                return u
    except Exception:  # noqa: BLE001 - giải mã không được thì thôi
        pass
    return link


def ten_mien(link):
    try:
        return urlparse(link).netloc.lower().replace("www.", "")
    except ValueError:
        return ""


def _khop_mien(m, d):
    return m == d or m.endswith("." + d)


def la_bao_chinh_thong(mien):
    m = (mien or "").lower().replace("www.", "")
    if not m or "google." in m or "bing." in m:
        return False
    if m.endswith(".gov.vn") or m.endswith(".edu.vn"):
        return True
    if any(_khop_mien(m, b[1]) for b in BAO.values()) or any(_khop_mien(m, d) for d in THEM_BAO_CHINH_THONG):
        return True
    return bool(re.match(r"^(bao|tapchi)[a-z0-9-]+\.(vn|com\.vn|org\.vn|net\.vn)$", m))


def ten_theo_mien(mien):
    for b in BAO.values():
        if _khop_mien(mien, b[1]):
            return b[0]
    return ""


def ten_nguon(t):
    """Tên báo hiển thị: ưu tiên tên trong BAO, nếu nguồn chỉ là tên miền trần thì đổi sang tên báo."""
    nguon = t.get("source") or ""
    if not nguon or re.fullmatch(r"[\w.-]+\.[a-z]{2,}", nguon.lower()):
        return ten_theo_mien(t.get("mien", "")) or nguon or t.get("mien", "")
    return nguon


def doc_rss(du_lieu, nguon_mac_dinh=""):
    """Đọc RSS 2.0 -> danh sách tin thô."""
    cay = ET.fromstring(du_lieu)
    ds = []
    for it in cay.iter("item"):
        tieu_de = lam_sach(it.findtext("title"))
        link = (it.findtext("link") or "").strip()
        mo_ta = lam_sach(it.findtext("description"))
        ngay = doc_ngay(it.findtext("pubDate"))
        nguon, nguon_url = "", ""
        for el in it:  # <source url="..."> (Google) hoặc <News:Source> (Bing)
            if el.tag.lower().endswith("source") and el.text:
                nguon = el.text.strip()
                nguon_url = el.get("url") or ""
        if not tieu_de or not link:
            continue
        ds.append({"title": tieu_de, "url": link_that(link), "summary": mo_ta, "dt": ngay,
                   "source": nguon or nguon_mac_dinh, "nguon_url": nguon_url})
    return ds


def thu(ham, lan=2, cho=2):
    """Thử lại khi lỗi mạng; lỗi 4xx (sai đường dẫn, bị chặn) thì bỏ ngay, không chờ."""
    loi = None
    for i in range(lan):
        try:
            return ham()
        except urllib.error.HTTPError as e:
            loi = e
            if e.code in (400, 401, 403, 404, 410):
                break
        except TimeoutError as e:
            loi = e
            break
        except Exception as e:  # noqa: BLE001 - lỗi mạng/định dạng thì thử lại
            loi = e
        time.sleep(cho * (i + 1))
    raise loi


# ===================== NGUỒN TIN =====================
def tim_bing(cau):
    url = f"https://www.bing.com/news/search?q={quote(cau)}&format=rss&setlang=vi&mkt=vi-VN&cc=VN"
    ds = doc_rss(tai(url))
    for t in ds:
        t["source"] = t["source"] or ten_mien(t["url"])
    return ds


def tim_google(cau):
    url = f"https://news.google.com/rss/search?q={quote(cau)}+when:30d&hl=vi&gl=VN&ceid=VN:vi"
    ds = doc_rss(tai(url))
    for t in ds:
        if t["source"] and t["title"].endswith(" - " + t["source"]):
            t["title"] = t["title"][: -len(t["source"]) - 3].strip()
        t["summary"] = ""  # mô tả của Google News chỉ lặp lại tiêu đề, không phải tóm tắt
        t["url"] = giai_ma_google(t["url"])
    return ds


_CACHE_KENH = {}


def doc_feed(url):
    """Đọc 1 kênh RSS (nhớ trong lần chạy để kênh dùng chung cho 2 tab chỉ tải 1 lần)."""
    if url not in _CACHE_KENH:
        _CACHE_KENH[url] = doc_rss(tai(url), ten_mien(url))
    return [dict(t) for t in _CACHE_KENH[url]]


def mo_ta_bai_goc(url):
    """Lấy thẻ og:description / description của bài gốc làm tóm tắt (khi RSS không có)."""
    if not url or "news.google.com" in url:
        return ""
    try:
        trang = tai(url, timeout=10)[:300000].decode("utf-8", "ignore")
    except Exception:  # noqa: BLE001
        return ""
    for mau in (r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:description',
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)'):
        m = re.search(mau, trang, re.I)
        if m:
            return lam_sach(m.group(1))
    return ""


# ===================== DÒ KÊNH RSS CỦA CÁC BÁO =====================
def la_kenh_rss(u, mien):
    p = urlparse(u)
    if not _khop_mien(p.netloc.lower().replace("www.", ""), mien):
        return False
    d = p.path.lower()
    return d.endswith((".rss", ".xml", ".atom")) or bool(re.search(r"/rss/[^/]+", d)) and not d.endswith((".htm", ".html"))


def kham_pha_kenh(bao):
    """Đọc trang liệt kê RSS (rồi tới trang chủ) của 1 báo, trả về (danh sách link kênh RSS, lỗi nếu có)."""
    _ten, mien, trang_ds, _tabs = bao
    loi = ""
    for trang in list(trang_ds) + [f"https://{mien}/"]:
        try:
            txt = thu(lambda: tai(trang, timeout=15), lan=2, cho=1)[:2_500_000].decode("utf-8", "ignore")
        except Exception as e:  # noqa: BLE001
            loi = f"{type(e).__name__}: {e}"[:120]
            continue
        dau = txt[:1500].lower()
        if "<rss" in dau or "<feed" in dau:     # chính địa chỉ này là một kênh RSS
            return [trang], ""
        thu_duoc = re.findall(r"""href\s*=\s*["']([^"'#\s]+)["']""", txt, re.I) + \
            re.findall(r"https?://[^\s\"'<>]+\.rss\b", txt, re.I)
        kenh = []
        for h in thu_duoc:
            u = urljoin(trang, html.unescape(h).strip())
            if la_kenh_rss(u, mien) and u not in kenh:
                kenh.append(u)
        if kenh:
            return kenh, ""
        loi = loi or "không thấy link RSS trong trang"
    return [], loi


def chon_kenh(kenh, tab):
    if len(kenh) <= 3:
        return list(kenh)
    rx = re.compile(SLUG_QUAN_TAM[tab])
    chon = [u for u in kenh if rx.search(bo_dau(unquote(urlparse(u).path)).lower())]
    return chon[:TOI_DA_KENH_MOI_BAO]


def tong_hop_kenh(da_biet):
    """Dò kênh của mọi báo (song song). Dò hụt thì dùng lại các kênh đã chạy tốt lần trước."""
    kenh_bao, ghi = {}, {}

    def lam(kv):
        khoa, bao = kv
        try:
            return khoa, kham_pha_kenh(bao)
        except Exception as e:  # noqa: BLE001
            return khoa, ([], f"{type(e).__name__}: {e}"[:120])

    with ThreadPoolExecutor(max_workers=8) as ex:
        for khoa, (kenh, loi) in ex.map(lam, BAO.items()):
            cu = [u for u in da_biet.get(khoa, []) if u not in kenh]
            kenh_bao[khoa] = kenh + cu
            ghi[khoa] = {"moi": len(kenh), "tu_truoc": len(cu), "loi": loi}
    return kenh_bao, ghi


# ===================== PHÂN LOẠI & CHỐNG TRÙNG =====================
def dem(mau, chuoi):
    return len(re.findall(mau, chuoi, re.I)) if mau else 0


def cham_diem(tin, muc):
    """Điểm khớp của 1 tin với 1 mục. -1 = bị loại."""
    # "AI" viết hoa thì tính là trí tuệ nhân tạo; "ai" thường (= ai đó, ai cũng) thì không
    tieu_de = re.sub(r"\bAI\b", "trí tuệ nhân tạo", tin["title"]).lower()
    mo_ta = re.sub(r"\bAI\b", "trí tuệ nhân tạo", tin["summary"]).lower()
    toan_bo = tieu_de + " " + mo_ta
    if muc.get("loai_tru") and re.search(muc["loai_tru"], tieu_de, re.I):
        return -1
    if muc.get("bat_buoc") and not re.search(muc["bat_buoc"], toan_bo, re.I):
        return -1
    diem = 2 * dem(muc["tu_khoa"], tieu_de) + dem(muc["tu_khoa"], mo_ta)
    if diem == 0:
        return 0
    if muc["key"] in tin.get("goi_y", ()):
        diem += 1.5  # tin tìm ra từ chính câu tìm kiếm của mục này
    return diem


def xu_ly_tab(ma_tab, cau_hinh, da_co_toan_cuc, kenh_tab):
    loi = {}
    ung_vien = []
    bi_loai = Counter()

    def lay_tim_kiem(muc, cau):
        kq = []
        for ten, ham in (("bing", tim_bing), ("google", tim_google)):
            try:
                ds = thu(lambda: ham(cau))
                for t in ds:
                    t["goi_y"] = {muc["key"]}
                kq += ds
                with _KHOA:
                    NK[ten][0] += 1
            except Exception as e:  # noqa: BLE001
                with _KHOA:
                    NK[ten][1] += 1
                    loi[f"{ten}:{cau}"] = f"{type(e).__name__}: {e}"[:150]
        return kq

    viec = [(m, c) for m in cau_hinh["muc"] for c in m["tim"]]
    if ma_tab == NT:   # báo địa phương không có RSS: tìm trực tiếp theo tên miền
        viec += [(m, f"site:{d} {CHU_DE_DIA_PHUONG[m['key']]}") for m in cau_hinh["muc"] for d in BAO_DIA_PHUONG]
    with ThreadPoolExecutor(max_workers=TIM_KIEM_SONG_SONG) as ex:
        for kq in ex.map(lambda mc: lay_tim_kiem(*mc), viec):
            ung_vien += kq

    def lay_feed(url):
        try:
            kq = thu(lambda: doc_feed(url))
            for t in kq:
                t["tin_cay"] = True   # kênh RSS của chính báo -> luôn là báo chính thống
            with _KHOA:
                GHI_KENH[url] = len(kq)
            return kq
        except Exception as e:  # noqa: BLE001
            with _KHOA:
                GHI_KENH[url] = -1
                loi[url] = f"{type(e).__name__}: {e}"[:150]
            return []

    ds_rss = list(dict.fromkeys(list(cau_hinh["rss"]) + list(kenh_tab)))
    with ThreadPoolExecutor(max_workers=KENH_SONG_SONG) as ex:
        for kq in ex.map(lay_feed, ds_rss):
            ung_vien += kq

    # Lọc: còn mới, tiếng Việt, báo chính thống, đúng địa phương (nếu tab yêu cầu)
    moc = datetime.now(VN) - timedelta(days=cau_hinh["so_ngay"])
    loc = []
    for t in ung_vien:
        if t["dt"] is None or t["dt"] < moc:
            continue
        if not co_tieng_viet(t["title"]):
            continue
        t["mien"] = ten_mien(t.get("nguon_url") or t["url"])
        if CHI_BAO_CHINH_THONG and not t.get("tin_cay") and not la_bao_chinh_thong(t["mien"]):
            bi_loai[t["mien"] or t.get("source") or "?"] += 1
            continue
        la_dia_phuong = any(_khop_mien(t["mien"], d) for d in BAO_DIA_PHUONG)   # báo Khánh Hòa: mặc định là tin địa phương
        if cau_hinh["bat_buoc"] and not la_dia_phuong \
                and not re.search(cau_hinh["bat_buoc"], t["title"] + " " + t["summary"], re.I):
            continue
        t["tu"] = tu_cua(t["title"])
        loc.append(t)
    NK["mien_bi_loai"].update(bi_loai)

    # Chống trùng: cùng link, hoặc tiêu đề giống >= NGUONG_TRUNG (cùng 1 sự kiện đăng ở nhiều báo).
    # Giữ bản mới nhất; gộp gợi ý mục của các bản trùng.
    loc.sort(key=lambda t: t["dt"], reverse=True)
    giu = []
    for t in loc:
        trung, muc_giong = None, 0
        for g in giu + da_co_toan_cuc:
            muc_giong = 1.0 if t["url"] == g["url"] else giong_nhau(t["tu"], g["tu"])
            if muc_giong >= NGUONG_TRUNG:
                trung = g
                break
        if trung is None:
            giu.append(t)
        elif any(trung is g for g in giu):
            trung["goi_y"] = set(trung.get("goi_y", ())) | set(t.get("goi_y", ()))
            # chỉ mượn tóm tắt khi gần như chắc chắn cùng 1 bài (tránh gán nhầm tóm tắt tin "giá vàng hôm qua")
            if not trung["summary"] and t["summary"] and muc_giong >= 0.9:
                trung["summary"] = t["summary"]

    # Phân loại: mỗi tin vào DUY NHẤT 1 mục có điểm cao nhất (mục đứng trước thắng khi bằng điểm)
    ket_qua = {m["key"]: [] for m in cau_hinh["muc"]}
    for t in giu:
        tot, diem_tot = None, 0
        for m in cau_hinh["muc"]:
            d = cham_diem(t, m)
            if d > diem_tot:
                tot, diem_tot = m["key"], d
        if tot:
            ket_qua[tot].append(t)

    for k in ket_qua:
        ket_qua[k].sort(key=lambda t: t["dt"], reverse=True)
        ket_qua[k] = ket_qua[k][:SO_TIN_MOI_MUC]
        da_co_toan_cuc += ket_qua[k]

    # Bổ sung tóm tắt từ bài gốc cho tin chưa có
    thieu = [t for k in ket_qua for t in ket_qua[k] if not t["summary"]][:80]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for t, mo_ta in zip(thieu, ex.map(lambda t: mo_ta_bai_goc(t["url"]), thieu)):
            t["summary"] = mo_ta

    def ra_json(t):
        tom_tat = t["summary"]
        if chuan(tom_tat).strip() == chuan(t["title"]).strip():
            tom_tat = ""
        if len(tom_tat) > DO_DAI_TOM_TAT:
            tom_tat = tom_tat[:DO_DAI_TOM_TAT].rsplit(" ", 1)[0] + "…"
        return {"title": t["title"], "summary": tom_tat, "url": t["url"], "source": ten_nguon(t),
                "date": t["dt"].strftime("%Y-%m-%d %H:%M")}

    sections = [{"key": m["key"], "name": m["ten"], "items": [ra_json(t) for t in ket_qua[m["key"]]]}
                for m in cau_hinh["muc"]]
    print(f"[{ma_tab}] {len(ung_vien)} tin thô -> {len(loc)} hợp lệ -> {len(giu)} sau chống trùng; "
          + ", ".join(f"{s['name']}: {len(s['items'])}" for s in sections)
          + f"; {len(ds_rss)} kênh RSS, lỗi {len(loi)}, loại {sum(bi_loai.values())} tin nguồn lạ")
    return {"name": cau_hinh["ten"], "sections": sections, "failed": dict(list(loi.items())[:12]), "n_failed": len(loi)}


# ===================== THỜI TIẾT (Open-Meteo, không cần key) =====================
def lay_thoi_tiet():
    url = ("https://api.open-meteo.com/v1/forecast?latitude=12.2388&longitude=109.1967"
           "&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
           "precipitation_probability_max,wind_speed_10m_max&timezone=Asia%2FHo_Chi_Minh&forecast_days=7")
    try:
        return thu(lambda: json.loads(tai(url)))
    except Exception as e:  # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}"}


def doc_json(ten):
    try:
        return json.loads((THU_MUC / ten).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def main():
    bat_dau = time.time()
    da_biet = doc_json("nguon_rss.json").get("tot", {})
    kenh_bao, ghi_bao = tong_hop_kenh(da_biet)
    co_kenh = sum(1 for v in kenh_bao.values() if v)
    print(f"Dò RSS: {co_kenh}/{len(BAO)} báo có kênh, tổng {sum(len(v) for v in kenh_bao.values())} kênh")
    kenh_theo_tab = {tab: [] for tab in TAB}
    for khoa, bao in BAO.items():
        for tab in bao[3]:
            kenh_theo_tab[tab] += chon_kenh(kenh_bao[khoa], tab)

    da_co = []  # dùng chung cho cả 3 tab -> một tin không xuất hiện ở 2 tab
    ket_qua = {"meta": {"fetched_at": datetime.now(VN).strftime("%Y-%m-%d %H:%M"),
                        "note": "Tin tự động từ RSS các báo chính thống, Bing News, Google News. Không cần API key."}}
    for ma_tab, cau_hinh in TAB.items():
        ket_qua[ma_tab] = xu_ly_tab(ma_tab, cau_hinh, da_co, kenh_theo_tab[ma_tab])
    ket_qua["weather"] = lay_thoi_tiet()

    # An toàn: nếu lần này lấy được quá ít (mất mạng), giữ lại mục cũ thay vì ghi đè bằng rỗng
    cu = doc_json("tin.json")
    for ma_tab in TAB:
        cu_tab = {s["key"]: s for s in (cu.get(ma_tab) or {}).get("sections", [])}
        for s in ket_qua[ma_tab]["sections"]:
            if not s["items"] and cu_tab.get(s["key"], {}).get("items"):
                s["items"] = cu_tab[s["key"]]["items"]
                s["stale"] = True
    if "error" in ket_qua["weather"] and cu.get("weather") and "error" not in cu["weather"]:
        ket_qua["weather"] = cu["weather"]

    # Nhật ký chẩn đoán (để biết nguồn nào hoạt động) + nhớ các kênh RSS đã chạy tốt
    tot = {k: [u for u in v if GHI_KENH.get(u, -1) >= 0] for k, v in kenh_bao.items()}
    ket_qua["meta"]["nguon"] = {
        "bao_co_kenh": co_kenh, "bao_tong": len(BAO),
        "kenh_tot": sum(1 for v in GHI_KENH.values() if v >= 0), "kenh_loi": sum(1 for v in GHI_KENH.values() if v < 0),
        "bing": NK["bing"], "google": NK["google"],
        "bao_khong_co_kenh": [BAO[k][0] for k, v in kenh_bao.items() if not v],
        "mien_bi_loai": [f"{m} ({n})" for m, n in NK["mien_bi_loai"].most_common(12)],
    }
    (THU_MUC / "tin.json").write_text(json.dumps(ket_qua, ensure_ascii=False, indent=1), encoding="utf-8")
    if any(tot.values()):   # chỉ ghi đè danh sách kênh tốt khi lần này có kênh chạy được
        (THU_MUC / "nguon_rss.json").write_text(json.dumps(
            {"updated": ket_qua["meta"]["fetched_at"], "tot": tot}, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"Xong sau {time.time() - bat_dau:.0f} giây. Xem data/tin.json (meta.nguon cho biết nguồn nào hoạt động)")


if __name__ == "__main__":
    main()
