"""Kiểm tra offline (không cần mạng, không cần trình duyệt) các hàm đọc/tính của fetch_xe.py.
Chạy:  python test_fetch_xe.py"""
import json, os, sys, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bs4 import BeautifulSoup
import fetch_xe as F

CFG = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "xe_cau_hinh.json"), encoding="utf-8"))
HANG = {h["hang"]: h for h in CFG["hang"]}
def dong(hang, ten): return next(d for d in HANG[hang]["dong"] if d["dong"] == ten)

ok = 0
def check(name, cond, extra=""):
    global ok
    if not cond:
        print("SAI:", name, extra); sys.exit(1)
    ok += 1

# 1. tìm giá trong chuỗi
check("gia nhom", F.tim_gia("Giá: 488.000.000 VNĐ") == [488_000_000])
check("gia trieu", F.tim_gia("Honda City L · 539 triệu VNĐ") == [539_000_000])
check("gia ty phay", F.tim_gia("Giá từ 4,415 tỷ đồng") == [4_415_000_000])
check("gia ty+trieu", F.tim_gia("1 tỷ 198 triệu") == [1_198_000_000])
check("khong phai gia", F.tim_gia("Kích thước 4425 x 1730 x 1475, hotline 1800 1524, năm 2026") == [])
check("ngoai khoang", F.tim_gia("Phụ phí 50.000 đồng") == [])

# 2. trích giá kiểu bảng Toyota (mỗi ô một dòng) + loại dòng ưu đãi/phí
TOYOTA_TXT = """Hatchback
Wigo G
405.000.000
Sedan
Vios 1.5E MT
458.000.000
Vios 1.5E CVT
488.000.000
Vios 1.5G CVT
545.000.000
Yaris Cross HEV
728.000.000
Fortuner Legender 2.7AT 4x4
1.395.000.000
Land Cruiser 300
4.580.000.000
Land Cruiser Prado
3.480.000.000
Phí cấp biển số: 14.000.000 đồng
Giảm giá 50% lệ phí trước bạ, trị giá 40.000.000 đồng
Trả góp từ 5.000.000 đồng/tháng
"""
g = F.trich_gia(TOYOTA_TXT)
d = dict(g)
check("toyota so dong", len(g) == 8, g)
check("vios cvt", d["Vios 1.5E CVT"] == 488_000_000)
check("bo phi/uu dai", all("Phí" not in n and "Giảm" not in n for n, _ in g))
tx = HANG["Toyota"]
vios = [(n, p) for n, p in g if F.thuoc_dong(n, dong("Toyota", "Vios"))]
check("vios 3 ban", len(vios) == 3, vios)
lc300 = [n for n, p in g if F.thuoc_dong(n, dong("Toyota", "Land Cruiser 300"))]
check("lc300 khong an Prado", lc300 == ["Land Cruiser 300"], lc300)
prado = [n for n, p in g if F.thuoc_dong(n, dong("Toyota", "Land Cruiser Prado"))]
check("prado", prado == ["Land Cruiser Prado"], prado)
check("ten phien ban", F.ten_phien_ban("Vios 1.5E CVT", "Toyota", "Vios") == "1.5E CVT")
check("ten phien ban mau", F.ten_phien_ban("Vios 1.5G CVT (Trắng ngọc trai)", "Toyota", "Vios") == "1.5G CVT")
check("ten rong", F.ten_phien_ban("Toyota Wigo", "Toyota", "Wigo") == "Tiêu chuẩn")

# 3. nhãn "Giá" đứng riêng, tên phiên bản ở dòng trên
TXT2 = "VIOS 1.5E-CVT\nGiá:\n488.000.000 VNĐ\nYaris Cross từ\n650.000.000 VNĐ"
g2 = F.trich_gia(TXT2)
check("nhan o dong tren", g2[0] == ("VIOS 1.5E-CVT", 488_000_000), g2)

# 4. nhận diện dòng xe giống nhau
H = HANG["Honda"]
check("civic != type r", F.thuoc_dong("Civic Type R", dong("Honda", "Civic")) is False)
check("type r", F.thuoc_dong("Civic Type R", dong("Honda", "Civic Type R")) is True)
check("civic", F.thuoc_dong("Civic RS", dong("Honda", "Civic")) is True)
check("hr-v", F.thuoc_dong("HR-V L", dong("Honda", "HR-V")) is True)
check("cr-v ko an hr-v", F.thuoc_dong("HR-V L", dong("Honda", "CR-V")) is False)
K = HANG["Kia"]
check("carens vs clavis", F.thuoc_dong("Carens Clavis HEV", dong("Kia", "Carens")) is False and F.thuoc_dong("Carens Clavis HEV", dong("Kia", "Carens Clavis")) is True)
V = HANG["VinFast"]
check("vf5 vs vf50", F.thuoc_dong("VF 5 Plus", dong("VinFast", "VF 5")) is True and F.thuoc_dong("VF 50", dong("VinFast", "VF 5")) is False)
check("vf3", F.thuoc_dong("VinFast VF3", dong("VinFast", "VF 3")) is True)
M = HANG["Mitsubishi"]
check("xpander cross", F.thuoc_dong("Xpander Cross", dong("Mitsubishi", "Xpander")) is False and F.thuoc_dong("Xpander Cross", dong("Mitsubishi", "Xpander Cross")) is True)

# 5. chọn trang xe từ danh sách liên kết
links = [("https://www.honda.com.vn/o-to/city", "City"), ("https://www.honda.com.vn/o-to/civic", "Civic"),
         ("https://www.honda.com.vn/o-to/civic-type-r", "Civic Type R"), ("https://www.honda.com.vn/tin-tuc/honda-city-2026", "Honda City 2026"),
         ("https://www.honda.com.vn/o-to/cr-v", "CR-V"), ("https://www.honda.com.vn/o-to/hr-v", "HR-V"), ("https://www.honda.com.vn/dai-ly/city", "x")]
check("chon city", F.chon_trang(links, dong("Honda", "City")) == "https://www.honda.com.vn/o-to/city")
check("chon civic", F.chon_trang(links, dong("Honda", "Civic")) == "https://www.honda.com.vn/o-to/civic")
check("chon type r", F.chon_trang(links, dong("Honda", "Civic Type R")) == "https://www.honda.com.vn/o-to/civic-type-r")
check("chon cr-v", F.chon_trang(links, dong("Honda", "CR-V")) == "https://www.honda.com.vn/o-to/cr-v")
check("khong co -> None", F.chon_trang(links, dong("Honda", "Accord")) is None)

# 6. bảng thông số nhiều cột có tiêu đề + nhóm
HTML = """<html><body><table>
<thead><tr><th>Thông số</th><th>1.5E CVT</th><th>1.5G CVT</th></tr></thead>
<tr><td colspan=3>Kích thước</td></tr>
<tr><td>Kích thước tổng thể (D x R x C) (mm)</td><td>4.425 x 1.730 x 1.475</td><td>4.425 x 1.730 x 1.475</td></tr>
<tr><td>Chiều dài cơ sở (mm)</td><td>2.550</td><td>2.550</td></tr>
<tr><td>Khoảng sáng gầm xe (mm)</td><td>133</td><td>133</td></tr>
<tr><td colspan=3>Động cơ</td></tr>
<tr><td>Loại động cơ</td><td>2NR-FE</td><td>2NR-FE</td></tr>
<tr><td>Dung tích xi lanh (cc)</td><td>1.496</td><td>1.496</td></tr>
<tr><td>Công suất tối đa (kW (HP)/vòng/phút)</td><td>79 (107)/6.000</td><td>79 (107)/6.000</td></tr>
<tr><td>Hộp số</td><td>CVT</td><td>CVT</td></tr>
<tr><td>Số túi khí</td><td>3</td><td>7</td></tr>
<tr><td colspan=3>Tiêu thụ nhiên liệu</td></tr>
<tr><td>Kết hợp</td><td>5,86</td><td>5,86</td></tr>
<tr><td>Số chỗ ngồi</td><td>5</td><td>5</td></tr>
</table></body></html>"""
soup = BeautifulSoup(HTML, "lxml")
pb, chung = F.trich_bang(soup)
check("2 cot phien ban", set(pb) == {"1.5E CVT", "1.5G CVT"}, list(pb))
c = F.chuan_hoa(pb["1.5G CVT"])
check("kich thuoc", c.get("kich_thuoc", "").startswith("4.425"), c)
check("co so", c.get("chieu_dai_co_so") == "2.550", c)
check("sang gam", c.get("khoang_sang_gam") == "133")
check("dong co", c.get("dong_co") == "2NR-FE", c)
check("dung tich", c.get("dung_tich_xi_lanh") == "1.496", c)
check("tui khi khac nhau", c.get("tui_khi") == "7" and F.chuan_hoa(pb["1.5E CVT"]).get("tui_khi") == "3")
check("tieu thu theo nhom", c.get("tieu_thu") == "5,86", c)
check("so cho", c.get("so_cho") == "5")
check("cong suat", c.get("cong_suat", "").startswith("79"))

# bảng hai cột + dl + tab
HTML2 = """<table><tr><td>Chiều dài cơ sở</td><td>2.620 mm</td></tr><tr><td>Động cơ</td><td>Hybrid 1.5L</td></tr></table>
<dl><dt>Hộp số</dt><dd>e-CVT</dd></dl>"""
pb2, ch2 = F.trich_bang(BeautifulSoup(HTML2, "lxml"))
check("bang 2 cot -> chung", ("Chiều dài cơ sở", "2.620 mm") in ch2 and ("Hộp số", "e-CVT") in ch2, ch2)
pb3, ch3 = F.trich_bang(BeautifulSoup(HTML2, "lxml"), "Bản HEV")
check("tab -> phien ban", "Bản HEV" in pb3 and len(pb3["Bản HEV"]) == 3, pb3)

# 7. ghép tên phiên bản giá ↔ thông số
bo = {"vios", "toyota"}
check("ghep dung", F.ghep_ten("1.5E CVT", "1.5E CVT", bo) == 1.0)
check("ghep phan biet MT/CVT", F.ghep_ten("1.5E MT", "1.5E CVT", bo) < 0.5)
check("ghep khac ky hieu", F.ghep_ten("1.5E-CVT", "1.5E CVT", bo) >= 0.5)

# 8. ảnh
HTML3 = """<html><head><meta property="og:image" content="/Resources/Vehicles/318/banner.png"></head><body>
<img src="/img/logo.png"><img data-src="/media/vios/exterior-1.jpg" alt="Toyota Vios"><img src="/x/icon.svg">
<img srcset="/a/small.jpg 400w, /a/big.jpg 1200w"><div style="background-image:url('/b/hero-vios.webp')"></div></body></html>"""
anh = F.trich_anh(BeautifulSoup(HTML3, "lxml"), "https://www.toyota.com.vn/vios", dong("Toyota", "Vios"))
check("anh og dau tien", anh[0] == "https://www.toyota.com.vn/Resources/Vehicles/318/banner.png", anh)
check("anh bo logo/svg", not any("logo" in u or ".svg" in u for u in anh), anh)
check("anh srcset lon", "https://www.toyota.com.vn/a/big.jpg" in anh, anh)
check("anh nen", "https://www.toyota.com.vn/b/hero-vios.webp" in anh, anh)

# 9. giá lăn bánh — đối chiếu VnExpress: Corolla Cross 1.8V 820 triệu
lp = CFG["lephi"]
lb = F.lan_banh(820_000_000, 5, "xe_con", False, lp)
check("lan banh CC", lb == {"khanh_hoa_kv2": 904_477_000, "ha_noi_tphcm_kv1": 918_337_000}, lb)
lb7 = F.lan_banh(730_000_000, 7, "xe_con", False, lp)
check("lan banh 7 cho", lb7["khanh_hoa_kv2"] == 730_000_000 + 73_000_000 + 140_000 + 340_000 + 1_560_000 + 794_000, lb7)
check("ban tai none", F.lan_banh(632_000_000, 5, "ban_tai", False, lp) is None)
check("chua ro cho none", F.lan_banh(1_198_000_000, None, "xe_con", False, lp) is None)
lbe = F.lan_banh(300_000_000, 5, "xe_con", True, lp)
check("xe dien 0%", lbe["khanh_hoa_kv2"] == 300_000_000 + 140_000 + 340_000 + 1_560_000 + 437_000, lbe)
# khớp toàn bộ file giá Toyota đã kiểm tra trước đó (nếu có)
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toyota_gia.json")
if os.path.exists(p):
    for x in json.load(open(p, encoding="utf-8"))["xe"]:
        seats = x["cho_ngoi"]
        exp = F.lan_banh(x["gia_niem_yet"], seats, "ban_tai" if x["dong"] == "Hilux" else "xe_con", False, lp)
        check("khop toyota_gia " + x["dong"] + " " + x["phien_ban"], (exp or {}).get("khanh_hoa_kv2") == (x["lan_banh"] or {}).get("khanh_hoa_kv2"))

# 10. cấu hình
tong = sum(len(h["dong"]) for h in CFG["hang"])
check("so dong xe", tong >= 55, tong)
for h in CFG["hang"]:
    for dd in h["dong"]:
        check("co tu khoa " + dd["dong"], dd.get("tu_khoa"))
# mỗi dòng xe trong gia_xe.json đều có trong cấu hình
gx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gia_xe.json")
if os.path.exists(gx):
    ten = {(h["hang"], F.kd(d["dong"])) for h in CFG["hang"] for d in h["dong"]}
    thieu = [(m["hang"], m["dong"]) for m in json.load(open(gx, encoding="utf-8"))["xe"] if (m["hang"], F.kd(m["dong"])) not in ten]
    print("Dòng trong gia_xe.json chưa có trong cấu hình:", thieu)

# 11. tích hợp: dòng xe đầy đủ với trình duyệt giả
from PIL import Image
class GiaBr:
    def __init__(self, pages): self.pages = pages; self.imgs = 0
    def lay(self, url, mo_rong=True):
        h = self.pages.get(url)
        return ([(None, h)], None) if h else (None, "HTTP 404")
    def tai_bytes(self, url):
        b = io.BytesIO(); Image.effect_noise((1400, 800), 60 + hash(url) % 50).convert("RGB").save(b, "PNG"); return b.getvalue()
PAGE_VIOS = HTML.replace("<body>", '<body><h1>Toyota Vios</h1><div>Yaris Cross từ 650.000.000 VNĐ</div><img src="/media/vios/exterior-1.jpg" alt="Vios"><img src="/media/vios/exterior-2.jpg" alt="Vios">') .replace("<head>", "<head>")
PAGE_VIOS = PAGE_VIOS.replace("<html>", '<html><head><meta property="og:image" content="/Resources/Vehicles/318/banner.png"></head>')
br = GiaBr({"https://www.toyota.com.vn/vios": PAGE_VIOS})
import fetch_xe as FX
FX.ANH_DIR = os.path.join("/tmp", "xe_anh_test")
hc = HANG["Toyota"]; dc = dong("Toyota", "Vios")
seed = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "toyota_gia.json"), encoding="utf-8")) if os.path.exists("toyota_gia.json") else None
kq = FX.xu_ly_dong(br, hc, dc, [("https://www.toyota.com.vn/vios", "Vios")], [("https://www.toyota.com.vn/tin-tuc/thong-tin-bo-tro/gia-toyota-45580", TOYOTA_TXT)], CFG, None, seed, True, "2026-11-06")
check("tich hop: 3 phien ban", len(kq["phien_ban"]) == 3, [p["ten"] for p in kq["phien_ban"]])
check("tich hop: sap tang dan", [p["gia_niem_yet"] for p in kq["phien_ban"]] == [458_000_000, 488_000_000, 545_000_000])
cvt = next(p for p in kq["phien_ban"] if p["ten"] == "1.5E CVT")
check("tich hop: ghep thong so 1.5E CVT", cvt["thong_so"]["chuan"].get("tui_khi") == "3", cvt["thong_so"]["chuan"])
g = next(p for p in kq["phien_ban"] if p["ten"] == "1.5G CVT")
check("tich hop: ghep thong so 1.5G CVT", g["thong_so"]["chuan"].get("tui_khi") == "7")
mt = next(p for p in kq["phien_ban"] if p["ten"] == "1.5E MT")
check("tich hop: ban MT khong bi gan thong so CVT", mt["thong_so"]["chuan"] == {}, mt["thong_so"]["chuan"])
check("tich hop: lan banh", cvt["lan_banh"]["khanh_hoa_kv2"] == 488_000_000 + 48_800_000 + 140_000 + 340_000 + 1_560_000 + 437_000, cvt["lan_banh"])
check("tich hop: nguon bang gia hang", cvt["nguon_gia"]["loai"] == "bang_gia_hang" and cvt["muc_tin_cay"] == "chinh_hang")
check("tich hop: khong an gia Yaris Cross", all(p["gia_niem_yet"] != 650_000_000 for p in kq["phien_ban"]))
check("tich hop: anh", len(kq["hinh_anh"]) >= 2 and os.path.exists(os.path.join("/tmp/xe_anh_test", "toyota-vios-1.webp")), kq["hinh_anh"])
check("tich hop: thong so chung", kq["thong_so_chung"].get("chieu_dai_co_so") is None)  # bảng 3 cột có tiêu đề -> theo phiên bản
check("tich hop: gia_tu", kq["gia_tu"] == 458_000_000)
check("tich hop: thieu", "gia" not in kq["thieu"] and "hinh_anh" not in kq["thieu"], kq["thieu"])
# không tìm thấy trang + có seed -> dùng giá kiểm tay, ghi chú rõ
kq2 = FX.xu_ly_dong(GiaBr({}), hc, dc, [], [], CFG, None, seed, True, "2026-11-06")
check("khong trang: dung seed", len(kq2["phien_ban"]) == 3 and kq2["phien_ban"][0]["muc_tin_cay"] == "kiem_tay_truoc_do", kq2["phien_ban"][:1])
check("khong trang: trang thai", kq2["trang_thai"] == "khong_tim_thay_trang" and "trang_xe" in kq2["thieu"], kq2["trang_thai"])
# hãng không có giá + không seed: không bịa
kq3 = FX.xu_ly_dong(GiaBr({}), HANG["Kia"], dong("Kia", "Seltos"), [], [], CFG, None, None, True, "2026-11-06")
check("khong bia gia", kq3["phien_ban"] == [] and kq3["gia_tu"] is None and "gia" in kq3["thieu"])
print("TẤT CẢ ĐẠT:", ok, "kiểm tra")
