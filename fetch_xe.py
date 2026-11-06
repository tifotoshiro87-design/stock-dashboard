#!/usr/bin/env python3
"""fetch_xe.py — lấy giá niêm yết, thông số, hình ảnh từng dòng xe từ TRANG CHÍNH HÃNG, tự tính giá lăn bánh.

Chạy trên GitHub Actions (workflow xe-chi-tiet.yml). Kết quả:
  data/xe_chi_tiet.json  — dữ liệu từng dòng xe, giá sắp từ thấp đến cao
  data/xe_bao_cao.json   — báo cáo: xe nào lấy đủ, xe nào thiếu gì, trang nào lỗi
  data/xe_anh/*.webp     — ảnh tổng quan tải về từ trang hãng

Nguyên tắc (theo yêu cầu của người dùng):
  - Không bịa số: mục nào không lấy được thì để trống và ghi rõ vào báo cáo.
  - Chỉ đọc trang công khai của hãng, tôn trọng robots.txt, cách nhau >= 2 giây giữa các lần tải,
    không vượt CAPTCHA/đăng nhập.
  - Mỗi giá ghi rõ nguồn (địa chỉ trang + ngày) và mức tin cậy.
Cách chạy thử một hãng/dòng:  python fetch_xe.py --hang Toyota --dong Vios
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.robotparser as robotparser
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
ANH_DIR = os.path.join(DATA, "xe_anh")
UA = "NewdayPersonalBot/1.0 (cong cu ca nhan, vai yeu cau moi tuan)"
DELAY = 2.0
VN = timezone(timedelta(hours=7))


# ───────────────────────── tiện ích chữ ─────────────────────────
def kd(s):
    """chữ thường, bỏ dấu tiếng Việt, gọn khoảng trắng"""
    s = unicodedata.normalize("NFD", s or "").replace("đ", "d").replace("Đ", "D")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s.lower()).strip()


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", kd(s)).strip("-")


def sach(s):
    return re.sub(r"\s+", " ", (s or "").replace("\xa0", " ")).strip()


# ───────────────────────── giá ─────────────────────────
GIA_NHOM = re.compile(r"(?<![\d.,])(\d{1,3}(?:[.,]\d{3}){2,3})(?![\d])")
GIA_TY = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*tỷ(?:\s*(\d+(?:[.,]\d+)?)\s*triệu)?", re.I)
GIA_TRIEU = re.compile(r"(?<![\d.,])(\d{3,4}(?:[.,]\d+)?)\s*triệu", re.I)
LOAI_GIA = re.compile(
    r"trả góp|/\s*tháng|mỗi tháng|giảm|ưu đãi|khuyến mại|khuyến mãi|hỗ trợ|lãi|trước bạ|phí|đặt cọc|"
    r"tiết kiệm|quà tặng|bảo hiểm|tặng|lăn bánh|tạm tính", re.I)
GIA_CHUNG = re.compile(
    r"^(giá( xe)?( ô tô)?|giá từ|giá bán|giá niêm yết|giá bán lẻ( đề xuất| khuyến nghị)?|giá lẻ|từ|chỉ từ|vnd|vnđ|đồng)\W*$", re.I)
MAU = re.compile(
    r"\(?\s*(màu\s+)?(trắng ngọc trai|trắng|đen|đỏ|xanh|bạc|xám|nâu|cam|vàng|hai tông màu|2 tông màu|tông màu)[^)]*\)?\s*$", re.I)
GIA_MIN, GIA_MAX = 150_000_000, 15_000_000_000


def so(s):
    return float(s.replace(",", "."))


def tim_gia(line):
    """Trả về danh sách giá (đồng) tìm thấy trong một dòng."""
    out = []
    for m in GIA_NHOM.finditer(line):
        v = int(re.sub(r"[.,]", "", m.group(1)))
        out.append(v)
    for m in GIA_TY.finditer(line):
        v = so(m.group(1)) * 1_000_000_000
        if m.group(2):
            v += so(m.group(2)) * 1_000_000
        out.append(int(round(v)))
    for m in GIA_TRIEU.finditer(line):
        # bỏ nếu nằm trong cụm "x tỷ y triệu" đã tính ở trên
        pre = line[: m.start()]
        if re.search(r"tỷ\s*$", pre, re.I):
            continue
        out.append(int(round(so(m.group(1)) * 1_000_000)))
    return [v for v in out if GIA_MIN <= v <= GIA_MAX]


def bo_gia(line):
    l = GIA_NHOM.sub(" ", line)
    l = GIA_TY.sub(" ", l)
    l = GIA_TRIEU.sub(" ", l)
    l = re.sub(r"\b(vnđ|vnd|đồng|đ)\b", " ", l, flags=re.I)
    l = re.sub(r"[:·\-–|•*]+\s*$", "", sach(l))
    l = re.sub(r"^[:·\-–|•*\s]+", "", l)
    return sach(l)


def co_chu(s):
    return bool(re.search(r"[A-Za-zÀ-ỹ0-9]{2}", s or ""))


def trich_gia(text):
    """Từ văn bản trang → danh sách (nhãn, giá). Nhãn = tên phiên bản đứng cùng dòng hoặc ngay phía trên."""
    lines = [sach(l) for l in text.split("\n")]
    lines = [l for l in lines if l]
    out, seen = [], set()
    for i, l in enumerate(lines):
        if LOAI_GIA.search(l) or len(l) > 160:
            continue
        gs = tim_gia(l)
        if not gs:
            continue
        nhan = bo_gia(l)
        if len(nhan) < 3 or GIA_CHUNG.match(nhan) or not co_chu(nhan):
            nhan = ""
            for j in range(i - 1, max(-1, i - 5), -1):
                c = lines[j]
                if tim_gia(c) or LOAI_GIA.search(c) or len(c) > 80 or GIA_CHUNG.match(c) or not co_chu(c):
                    continue
                nhan = c
                break
        if not nhan:
            continue
        key = (kd(nhan), gs[0])
        if key in seen:
            continue
        seen.add(key)
        out.append((nhan, gs[0]))
    return out


# ───────────────────────── nhận diện dòng xe ─────────────────────────
def khop_tu_khoa(chuoi_kd, dong_cfg):
    """chuoi_kd đã bỏ dấu. True nếu chứa từ khóa của dòng xe và không chứa từ loại trừ."""
    for lt in dong_cfg.get("loai_tru", []):
        if re.search(r"(^|[^a-z0-9])" + re.escape(kd(lt)) + r"($|[^a-z0-9])", chuoi_kd):
            return False
    for tk in dong_cfg["tu_khoa"]:
        t = kd(tk)
        for v in {t, t.replace(" ", "-"), t.replace(" ", "")}:
            if re.search(r"(^|[^a-z0-9])" + re.escape(v) + r"($|[^a-z0-9])", chuoi_kd):
                return True
    return False


def thuoc_dong(nhan, dong_cfg):
    return khop_tu_khoa(kd(nhan), dong_cfg)


def ten_phien_ban(nhan, hang, dong):
    t = sach(nhan)
    t = re.sub(r"^(giá( xe)?( ô tô)?)\s*", "", t, flags=re.I)
    for tok in (hang, dong):
        t = re.sub(r"^\s*" + re.escape(tok) + r"\b[\s:\-–]*", "", t, flags=re.I)
    t = MAU.sub("", t)
    t = sach(t)
    return t or "Tiêu chuẩn"


# ───────────────────────── thông số ─────────────────────────
CHUAN = [  # (khóa, mẫu nhãn đã bỏ dấu)
    ("kich_thuoc", r"kich thuoc (tong the|ben ngoai)|\bd ?x ?r ?x ?c\b|dai x rong x cao"),
    ("chieu_dai_co_so", r"chieu dai co so"),
    ("khoang_sang_gam", r"khoang sang gam"),
    ("ban_kinh_quay_vong", r"ban kinh (vong )?quay"),
    ("trong_luong", r"(trong|khoi) luong (khong tai|ban than|bo)"),
    ("dung_tich_binh", r"dung tich binh|binh nhien lieu"),
    ("so_cho", r"so cho( ngoi)?$|so cho ngoi"),
    ("dung_tich_xi_lanh", r"dung tich (xy|xi) ?lanh|dung tich dong co|dung tich cong tac"),
    ("cong_suat", r"cong suat"),
    ("mo_men", r"mo men|momen"),
    ("hop_so", r"hop so"),
    ("dan_dong", r"dan dong|he dan dong"),
    ("tieu_thu", r"tieu thu nhien lieu.*(ket hop|tong hop|hon hop)|(ket hop|tong hop|hon hop).*tieu thu|^ket hop$"),
    ("nhien_lieu", r"^(loai )?nhien lieu$|loai nhien lieu"),
    ("dong_co", r"^(loai |kieu )?dong co$|kieu dong co|loai dong co|^dong co "),
    ("tui_khi", r"tui khi"),
    ("mam_lop", r"mam|la ?zang|vanh|kich thuoc lop|lop xe"),
    ("xuat_xu", r"xuat xu"),
]


def chuan_hoa(cap):
    """cap: [(nhãn, giá trị)] → dict các thông số chuẩn (lấy giá trị đầu tiên khớp)."""
    out = {}
    for nhan, gt in cap:
        l = kd(nhan)
        if not gt:
            continue
        for k, pat in CHUAN:
            if k not in out and re.search(pat, l):
                out[k] = gt
                break
    return out


def trich_bang(soup, nhan_tab=None):
    """Trả về (theo_phien_ban: {tên: [(nhãn,giá trị)]}, chung: [(nhãn,giá trị)])."""
    theo_pb, chung = {}, []
    for tb in soup.find_all("table"):
        trs = tb.find_all("tr")
        if not trs:
            continue
        hdr = None
        thead = tb.find("thead")
        first = trs[0]
        if thead and thead.find("tr"):
            first = thead.find("tr")
            hdr = [sach(c.get_text(" ")) for c in first.find_all(["th", "td"])]
        elif first.find_all("th") and not first.find_all("td") and len(first.find_all("th")) >= 3:
            hdr = [sach(c.get_text(" ")) for c in first.find_all("th")]
        nhom = ""
        for tr in trs:
            if tr is first and hdr is not None:
                continue
            cells = [sach(c.get_text(" ")) for c in tr.find_all(["th", "td"])]
            if len(cells) == 1 or (len(cells) > 1 and not any(cells[1:])):
                nhom = cells[0]
                continue
            if len(cells) < 2 or not cells[0]:
                continue
            nhan, vals = cells[0], cells[1:]
            if nhom and re.fullmatch(r"(kết hợp|trong đô thị|ngoài đô thị|đô thị|cao tốc|trước|sau|trước/sau)", nhan, re.I):
                nhan = f"{nhom} {nhan}"
            names = None
            if hdr:
                if len(hdr) == len(vals) + 1:
                    names = hdr[1:]
                elif len(hdr) == len(vals):
                    names = hdr
            if names and len(names) > 1:
                for n, v in zip(names, vals):
                    if n:
                        theo_pb.setdefault(n, []).append((nhan, v))
            elif nhan_tab and len(vals) == 1:
                theo_pb.setdefault(nhan_tab, []).append((nhan, vals[0]))
            else:
                chung.append((nhan, vals[0] if len(vals) == 1 else " / ".join(v for v in vals if v)))
    for dl in soup.find_all("dl"):
        dts, dds = dl.find_all("dt"), dl.find_all("dd")
        for a, b in zip(dts, dds):
            la, lb = sach(a.get_text(" ")), sach(b.get_text(" "))
            if la and lb and len(la) < 80:
                (theo_pb.setdefault(nhan_tab, []) if nhan_tab else chung).append((la, lb))
    return theo_pb, chung


def trich_cap_div(soup):
    """Dự phòng khi trang không dùng bảng: các khối 'nhãn – giá trị' trong phần tử có class thông số."""
    out = []
    for el in soup.find_all(class_=re.compile(r"(spec|param|thong-?so)[\w-]*(row|item|line)|(row|item|line)[\w-]*(spec|param|thong-?so)", re.I)):
        kids = [k for k in el.find_all(recursive=False)]
        if len(kids) == 2:
            a, b = sach(kids[0].get_text(" ")), sach(kids[1].get_text(" "))
            if a and b and len(a) < 60 and len(b) < 120:
                out.append((a, b))
    return out


def van_ban(soup):
    s = BeautifulSoup(str(soup), "lxml")
    for t in s(["script", "style", "noscript", "template"]):
        t.decompose()
    return s.get_text("\n")


# ───────────────────────── hình ảnh ─────────────────────────
BO_ANH = re.compile(r"logo|icon|favicon|sprite|avatar|flag|badge|qr|payment|social|facebook|youtube|zalo|loading|placeholder|\.svg|\.gif", re.I)
UU_TIEN_ANH = re.compile(r"banner|overview|exterior|ngoai-that|noi-that|interior|gallery|hero|thumb|main|360|key-?visual|kv", re.I)


def chon_srcset(srcset):
    best, bw = None, -1
    for part in (srcset or "").split(","):
        p = part.strip().split()
        if not p:
            continue
        w = 0
        if len(p) > 1:
            m = re.match(r"(\d+)(w|x)", p[1])
            if m:
                w = int(m.group(1)) * (1 if m.group(2) == "w" else 1000)
        if w >= bw:
            best, bw = p[0], w
    return best


def trich_anh(soup, base_url, dong_cfg=None):
    """Danh sách địa chỉ ảnh ứng viên, xếp theo độ ưu tiên (ảnh trang bìa/ngoại thất lên trước)."""
    cand = []

    def them(u, diem=0):
        if not u or u.startswith("data:"):
            return
        full = urljoin(base_url, u.strip())
        if not full.startswith("http") or BO_ANH.search(full):
            return
        if not re.search(r"\.(jpe?g|png|webp)(\?|$)", full, re.I) and "/Resources/" not in full and "/media/" not in full:
            return
        cand.append((full, diem))

    for m in soup.find_all("meta", attrs={"property": "og:image"}):
        them(m.get("content"), 50)
    for img in soup.find_all("img"):
        u = img.get("data-src") or img.get("data-lazy-src") or img.get("data-original") or chon_srcset(img.get("srcset")) or img.get("src")
        d = 0
        if UU_TIEN_ANH.search(u or ""):
            d += 10
        if dong_cfg and khop_tu_khoa(kd(u or "") + " " + kd(img.get("alt") or ""), dong_cfg):
            d += 8
        w = img.get("width")
        if w and str(w).isdigit() and int(w) < 200:
            continue
        them(u, d)
    for src in soup.find_all("source"):
        them(chon_srcset(src.get("srcset")), 5)
    for el in soup.find_all(style=re.compile(r"url\(")):
        m = re.search(r"url\(['\"]?([^'\")]+)", el.get("style", ""))
        if m:
            them(m.group(1), 6)
    out, seen = [], set()
    for u, d in sorted(cand, key=lambda x: -x[1]):
        k = u.split("?")[0]
        if k in seen:
            continue
        seen.add(k)
        out.append(u)
    return out


# ───────────────────────── giá lăn bánh ─────────────────────────
def lan_banh(gia, cho_ngoi, loai, dien, lp):
    """Trả về dict hai khu vực hoặc None nếu chưa tính được (bán tải/xe tải/chưa rõ số chỗ)."""
    if loai in ("ban_tai", "xe_tai") or not cho_ngoi:
        return None
    pct = lp["truoc_ba_xe_dien_pct"] if dien else lp["truoc_ba_pct"]
    bh = lp["bhtnds_duoi_6_cho"] if cho_ngoi < 6 else lp["bhtnds_6_den_11_cho"]
    chung = gia * pct // 100 + lp["dang_kiem"] + lp["duong_bo_nam"] + bh
    return {"khanh_hoa_kv2": gia + chung + lp["bien_so_kv2"], "ha_noi_tphcm_kv1": gia + chung + lp["bien_so_kv1"]}


# ───────────────────────── ghép phiên bản ─────────────────────────
def tokens_pb(ten, bo):
    t = set(re.findall(r"[a-z0-9.]+", kd(ten)))
    return {x for x in t if x not in bo and x not in {"xe", "ban", "phien", "gia"}}


def ghep_ten(ten_gia, ten_ts, bo):
    a, b = tokens_pb(ten_gia, bo), tokens_pb(ten_ts, bo)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ───────────────────────── trình duyệt ─────────────────────────
class TrinhDuyet:
    def __init__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.br = self._pw.chromium.launch()
        self.ctx = self.br.new_context(user_agent=UA, locale="vi-VN", viewport={"width": 1366, "height": 900})
        self.page = self.ctx.new_page()
        self._robots, self._cuoi = {}, {}

    def dong(self):
        try:
            self.br.close()
            self._pw.stop()
        except Exception:
            pass

    def duoc_phep(self, url):
        host = urlparse(url).netloc
        rp = self._robots.get(host)
        if rp is None:
            rp = robotparser.RobotFileParser()
            rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
            try:
                rp.read()
            except Exception:
                rp = False
            self._robots[host] = rp
        return True if rp is False else rp.can_fetch(UA, url)

    def cho(self, url):
        host = urlparse(url).netloc
        d = DELAY - (time.time() - self._cuoi.get(host, 0))
        if d > 0:
            time.sleep(d)
        self._cuoi[host] = time.time()

    def lay(self, url, mo_rong=True):
        """Tải trang, bung các mục thông số, đọc từng tab. Trả về (danh sách (nhãn_tab, html), lỗi)."""
        if not self.duoc_phep(url):
            return None, "robots.txt không cho phép"
        self.cho(url)
        p = self.page
        try:
            r = p.goto(url, wait_until="domcontentloaded", timeout=45000)
            if r is not None and r.status >= 400:
                return None, f"HTTP {r.status}"
            try:
                p.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            for _ in range(6):
                p.mouse.wheel(0, 1400)
                p.wait_for_timeout(350)
            snaps = []
            if mo_rong:
                self._bung(p)
            snaps.append((None, p.content()))
            if mo_rong:
                tabs = p.locator("[role=tab]")
                n = min(tabs.count(), 12)
                for i in range(n):
                    try:
                        t = tabs.nth(i)
                        nhan = sach(t.inner_text())
                        t.click(timeout=2000)
                        p.wait_for_timeout(500)
                        self._bung(p)
                        if nhan:
                            snaps.append((nhan, p.content()))
                    except Exception:
                        continue
            return snaps, None
        except Exception as e:
            return None, f"{type(e).__name__}: {str(e)[:120]}"

    @staticmethod
    def _bung(p):
        try:
            p.evaluate(
                """()=>{let n=0;const ok=e=>!(e.tagName=='A'&&e.getAttribute('href')&&e.getAttribute('href')!='#');
                document.querySelectorAll('[aria-expanded="false"],details:not([open])>summary,.accordion-header,.collapsible-header').forEach(e=>{if(n<80&&ok(e)){try{e.click();n++}catch(_){}}});
                document.querySelectorAll('button,a,span,div').forEach(e=>{const t=(e.innerText||'').trim().toLowerCase();
                 if(t.length<40&&/^(thông số( kỹ thuật)?|xem (thêm|tất cả|chi tiết)( thông số)?|tất cả thông số|mở rộng)$/.test(t)&&ok(e)&&n<100){try{e.click();n++}catch(_){}}})}""")
            p.wait_for_timeout(400)
        except Exception:
            pass

    def tai_bytes(self, url):
        if not self.duoc_phep(url):
            return None
        self.cho(url)
        try:
            r = self.ctx.request.get(url, timeout=30000)
            return r.body() if r.ok else None
        except Exception:
            return None


# ───────────────────────── khám phá địa chỉ trang xe ─────────────────────────
LOAI_PATH = re.compile(
    r"tin-tuc|news|khuyen-mai|uu-dai|dai-ly|showroom|phu-kien|dich-vu|bao-hanh|bao-duong|so-sanh|lai-thu|du-toan|catalogue|tai-ve|"
    r"download|tuyen-dung|lien-he|chinh-sach|dieu-khoan|bao-mat|dat-lich|tim-dai-ly|\.pdf|facebook|youtube|tiktok|zalo", re.I)
LIST_PATH = re.compile(r"o-to|oto|/xe|vehicle|san-pham|dong-xe|models?|cars?|danh-sach|find-a-car|passenger", re.I)


def cung_hang(url, hang_cfg):
    host = urlparse(url).netloc.lower()
    return any(host == d or host.endswith("." + d) for d in hang_cfg["ten_mien"])


def lay_link(html, base, hang_cfg):
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        h = a["href"].strip()
        if h.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        u = urljoin(base, h).split("#")[0]
        if not cung_hang(u, hang_cfg):
            continue
        txt = sach(a.get_text(" ")) + " " + sach(a.get("aria-label") or "") + " " + " ".join(sach(i.get("alt") or "") for i in a.find_all("img"))
        out.append((u, txt))
    return out


def diem_link(url, txt, dong_cfg):
    path = kd(urlparse(url).path)
    if LOAI_PATH.search(path):
        return 0
    tk_path = khop_tu_khoa(path, dong_cfg)
    tk_txt = khop_tu_khoa(kd(txt), dong_cfg)
    if not (tk_path or tk_txt):
        return 0
    depth = len([p for p in path.split("/") if p])
    return (10 if tk_path else 0) + (3 if tk_txt else 0) - 0.05 * len(path) - 0.3 * depth + 2


def chon_trang(links, dong_cfg):
    best, bs = None, 0
    for u, t in links:
        s = diem_link(u, t, dong_cfg)
        if s > bs:
            best, bs = u, s
    return best


def thu_link(br, hang_cfg, bao_loi):
    """Quét các trang bắt đầu và một tầng trang danh sách của hãng → danh sách (url, chữ)."""
    links, da = [], set()
    for u in hang_cfg["trang_bat_dau"]:
        snaps, err = br.lay(u, mo_rong=False)
        if err:
            bao_loi.append(f"{u}: {err}")
            continue
        da.add(u)
        links += lay_link(snaps[0][1], u, hang_cfg)
    ds = []
    for u, t in links:
        p = kd(urlparse(u).path)
        if u not in da and LIST_PATH.search(p) and not LOAI_PATH.search(p) and u not in ds:
            ds.append(u)
    for u in ds[:10]:
        snaps, err = br.lay(u, mo_rong=False)
        if err:
            continue
        links += lay_link(snaps[0][1], u, hang_cfg)
    return links


# ───────────────────────── xử lý một dòng xe ─────────────────────────
def gia_tham_chieu(hang, dong, gia_xe, seeds):
    for m in (gia_xe or {}).get("xe", []):
        if kd(m.get("hang")) == kd(hang) and kd(m.get("dong")) == kd(dong):
            return m["gia_tu"] * 1_000_000
    return None


def xu_ly_dong(br, hang_cfg, dong_cfg, links, texts_gia, cfg, gia_xe, seed, anh_cho_phep, ngay):
    hang, dong = hang_cfg["hang"], dong_cfg["dong"]
    sl = slug(f"{hang} {dong}")
    ghi_chu, thieu = [], []
    kq = {"hang": hang, "dong": dong, "slug": sl, "loai": dong_cfg.get("loai", "xe_con"), "trang_hang": None,
          "phien_ban": [], "thong_so_chung": {}, "hinh_anh": [], "ghi_chu": ghi_chu}
    url = dong_cfg.get("url") or chon_trang(links, dong_cfg)
    kq["trang_hang"] = url
    ung_gia = []  # (muc_uu_tien, nhan, gia, nguon_url)
    ts_pb, ts_chung, anh = {}, [], []

    soup0 = None
    if url:
        snaps, err = br.lay(url)
        if err:
            ghi_chu.append(f"Không tải được trang xe: {err}")
            thieu.append("trang_xe")
        else:
            soup0 = BeautifulSoup(snaps[0][1], "lxml")
            for nhan_tab, h in snaps:
                s = BeautifulSoup(h, "lxml")
                a, b = trich_bang(s, nhan_tab)
                for k, v in a.items():
                    ts_pb.setdefault(k, [])
                    ts_pb[k] += [x for x in v if x not in ts_pb[k]]
                ts_chung += [x for x in b if x not in ts_chung]
            if len(ts_chung) + sum(len(v) for v in ts_pb.values()) < 4:
                ts_chung += trich_cap_div(soup0)
            anh = trich_anh(soup0, url, dong_cfg)
            tx = van_ban(soup0)
            khac = [d for d in hang_cfg["dong"] if d is not dong_cfg]
            for nhan, g in trich_gia(tx):
                if thuoc_dong(nhan, dong_cfg) or not any(thuoc_dong(nhan, d) for d in khac):
                    ung_gia.append((1, nhan, g, url))
    else:
        ghi_chu.append("Không tìm thấy trang của dòng xe này trên website hãng (hãng có thể đã thôi bán hoặc đổi địa chỉ).")
        thieu.append("trang_xe")

    for u, tx in texts_gia:
        for nhan, g in trich_gia(tx):
            if thuoc_dong(nhan, dong_cfg):
                ung_gia.append((0, nhan, g, u))

    # gom theo phiên bản (khóa = tên phiên bản bỏ dấu), ưu tiên nguồn bảng giá hãng, trong cùng mức lấy giá thấp nhất
    pbs = {}
    for ut, nhan, g, u in sorted(ung_gia, key=lambda x: (x[0], x[2])):
        ten = ten_phien_ban(nhan, hang, dong)
        k = kd(ten)
        if k not in pbs:
            pbs[k] = {"ten": ten, "gia": g, "nguon": u, "ut": ut}
        elif pbs[k]["ut"] == ut and pbs[k]["gia"] != g:
            ghi_chu.append(f"Phiên bản '{ten}' có hai giá khác nhau trên cùng loại nguồn ({pbs[k]['gia']:,} và {g:,}); giữ giá thấp hơn, cần đối chiếu.".replace(",", "."))
        elif pbs[k]["ut"] != ut and pbs[k]["gia"] != g:
            ghi_chu.append(f"Phiên bản '{ten}': bảng giá hãng ghi {pbs[k]['gia']:,}, trang xe ghi {g:,}; dùng bảng giá hãng.".replace(",", "."))

    muc = "chinh_hang"
    if not pbs and seed:
        for s in seed.get("xe", []):
            if kd(s["dong"]) == kd(dong) and s.get("gia_niem_yet"):
                pbs[kd(s["phien_ban"])] = {"ten": s["phien_ban"], "gia": s["gia_niem_yet"], "nguon": s["nguon_gia"], "ut": 2, "seed": s}
        if pbs:
            ghi_chu.append("Không đọc được giá từ trang hãng lần này; dùng giá đã kiểm tay trước đó (xem nguồn trong từng phiên bản).")

    # ghép thông số với phiên bản
    bo = set(re.findall(r"[a-z0-9.]+", kd(dong))) | set(re.findall(r"[a-z0-9.]+", kd(hang)))
    cap_chung = list(ts_chung)
    chung_chuan = chuan_hoa(ts_chung)
    pb_ts = {}
    for ten_ts, cap in ts_pb.items():
        pb_ts[ten_ts] = cap
    versions = []
    dung = set()
    for k, v in pbs.items():
        ts, diem = None, 0.0
        for ten_ts in pb_ts:
            d = ghep_ten(v["ten"], ten_ts, bo)
            if d > diem and ten_ts not in dung:
                ts, diem = ten_ts, d
        if ts is None and len(pbs) == 1 and len(pb_ts) == 1:
            ts, diem = next(iter(pb_ts)), 1.0
        if ts is not None and diem >= 0.5:
            dung.add(ts)
            cap = pb_ts[ts]
        else:
            cap = []
        versions.append((v, cap))
    # nếu có bảng nhiều cột mà không ghép được phiên bản nào → giữ nguyên để người dùng xem
    chua_ghep = {t: c for t, c in pb_ts.items() if t not in dung}
    if chua_ghep and pbs:
        ghi_chu.append("Có cột thông số của phiên bản không ghép được với bảng giá: " + ", ".join(chua_ghep) + " (xem 'thong_so_chua_ghep').")
    if chua_ghep:
        kq["thong_so_chua_ghep"] = {t: [{"nhan": a, "gt": b} for a, b in c[:80]] for t, c in chua_ghep.items()}
    if not pbs and pb_ts:
        for t, c in pb_ts.items():
            versions.append(({"ten": t, "gia": None, "nguon": None, "ut": 9}, c))

    seats_cfg = dong_cfg.get("cho_ngoi")
    for v, cap in versions:
        ch = chuan_hoa(cap) if cap else {}
        merged = {**chung_chuan, **ch}
        cho = None
        m = re.search(r"\d+", merged.get("so_cho", ""))
        if m:
            cho = int(m.group(0))
            if not (2 <= cho <= 12):
                cho = None
        if cho is None:
            cho = seats_cfg
        ver = {"ten": v["ten"], "gia_niem_yet": v["gia"], "cho_ngoi": cho,
               "lan_banh": lan_banh(v["gia"], cho, kq["loai"], dong_cfg.get("dien", False), cfg["lephi"]) if v["gia"] else None,
               "nguon_gia": {"url": v["nguon"], "ngay": ngay, "loai": ("bang_gia_hang" if v["ut"] == 0 else "trang_xe_hang" if v["ut"] == 1 else "gia_kiem_tay_truoc_do")} if v["gia"] else None,
               "muc_tin_cay": ("chinh_hang" if v["ut"] in (0, 1) else "kiem_tay_truoc_do") if v["gia"] else None,
               "thong_so": {"chuan": ch, "tho": [{"nhan": a, "gt": b} for a, b in cap[:120]]}}
        if v["gia"] and not ver["lan_banh"] and kq["loai"] == "xe_con" and not cho:
            ver["lan_banh_ghi_chu"] = "chưa rõ số chỗ ngồi nên chưa tính lăn bánh"
        if kq["loai"] in ("ban_tai", "xe_tai"):
            ver["lan_banh_ghi_chu"] = "bán tải/xe tải tính lệ phí khác xe con, chưa tính"
        if dong_cfg.get("dien"):
            ver["lan_banh_ghi_chu"] = "xe điện: trước bạ 0% theo quy định hiện hành em biết, đối chiếu lại khi quy định đổi"
        versions_obj = ver
        kq["phien_ban"].append(versions_obj)
    kq["phien_ban"].sort(key=lambda x: (x["gia_niem_yet"] is None, x["gia_niem_yet"] or 0))
    kq["thong_so_chung"] = chung_chuan
    kq["thong_so_chung_tho"] = [{"nhan": a, "gt": b} for a, b in cap_chung[:120]]
    gias = [p["gia_niem_yet"] for p in kq["phien_ban"] if p["gia_niem_yet"]]
    kq["gia_tu"] = min(gias) if gias else None

    # đối chiếu giá tham chiếu (file gia_xe.json tổng hợp từ báo)
    ref = gia_tham_chieu(hang, dong, gia_xe, seed)
    if ref and gias and abs(min(gias) - ref) / ref > 0.02:
        ghi_chu.append(f"Giá thấp nhất {min(gias):,} lệch hơn 2% so với giá tham chiếu trong gia_xe.json ({ref:,}, nguồn báo); cần đối chiếu.".replace(",", "."))

    # tải ảnh
    if anh and anh_cho_phep:
        kq["hinh_anh"] = tai_anh(br, anh, sl, url, dong_cfg)
    if not gias:
        thieu.append("gia")
    if not (chung_chuan or any(p["thong_so"]["chuan"] for p in kq["phien_ban"])):
        thieu.append("thong_so")
    elif max([len(chung_chuan)] + [len(p["thong_so"]["chuan"]) for p in kq["phien_ban"]]) < 4:
        thieu.append("thong_so_it")
    if not kq["hinh_anh"]:
        thieu.append("hinh_anh")
    kq["thieu"] = thieu
    kq["trang_thai"] = "day_du" if not thieu else ("khong_tim_thay_trang" if "trang_xe" in thieu else "thieu_" + "_".join(thieu))
    return kq


def tai_anh(br, ds, sl, trang, dong_cfg, toi_da=5):
    from PIL import Image
    os.makedirs(ANH_DIR, exist_ok=True)
    out, hashes = [], set()
    for u in ds[:20]:
        if len(out) >= toi_da:
            break
        b = br.tai_bytes(u)
        if not b or len(b) < 8000:
            continue
        try:
            im = Image.open(io.BytesIO(b))
            im.load()
        except Exception:
            continue
        if im.width < 700 or im.width < im.height * 0.8:
            continue
        if im.width > 1200:
            im = im.resize((1200, int(im.height * 1200 / im.width)))
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        h = hashlib.md5(im.resize((32, 32)).tobytes()).hexdigest()
        if h in hashes:
            continue
        hashes.add(h)
        fn = f"{sl}-{len(out) + 1}.webp"
        im.save(os.path.join(ANH_DIR, fn), "WEBP", quality=80)
        out.append({"file": f"data/xe_anh/{fn}", "nguon": u, "trang": trang})
    return out


# ───────────────────────── chạy tổng ─────────────────────────
def doc_json(p, mac_dinh=None):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return mac_dinh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hang", help="chỉ chạy một hãng, ví dụ Toyota")
    ap.add_argument("--dong", help="chỉ chạy một dòng xe, ví dụ Vios")
    ap.add_argument("--khong-anh", action="store_true", help="không tải ảnh")
    args = ap.parse_args()

    cfg = doc_json(os.path.join(HERE, "xe_cau_hinh.json"))
    gia_xe = doc_json(os.path.join(HERE, "gia_xe.json")) or doc_json(os.path.join(DATA, "gia_xe.json"))
    cu = doc_json(os.path.join(DATA, "xe_chi_tiet.json"), {"xe": []})
    ngay = datetime.now(VN).strftime("%Y-%m-%d")
    os.makedirs(DATA, exist_ok=True)

    br = TrinhDuyet()
    ket_qua, bao_cao = [], {"ngay": ngay, "hang": {}, "xe": []}
    try:
        for hc in cfg["hang"]:
            if args.hang and kd(args.hang) != kd(hc["hang"]):
                continue
            loi_hang = []
            seed = doc_json(os.path.join(HERE, hc["gia_du_phong_file"])) if hc.get("gia_du_phong_file") else None
            texts = []
            for u in hc.get("trang_gia", []):
                snaps, err = br.lay(u, mo_rong=False)
                if err:
                    loi_hang.append(f"trang giá {u}: {err}")
                else:
                    texts.append((u, van_ban(BeautifulSoup(snaps[0][1], "lxml"))))
            links = thu_link(br, hc, loi_hang)
            if not links:
                loi_hang.append("không đọc được liên kết nào từ trang bắt đầu của hãng — kiểm tra 'trang_bat_dau' trong xe_cau_hinh.json")
            for dc in hc["dong"]:
                if args.dong and kd(args.dong) != kd(dc["dong"]):
                    continue
                try:
                    kq = xu_ly_dong(br, hc, dc, links, texts, cfg, gia_xe, seed, not args.khong_anh, ngay)
                except Exception as e:
                    kq = {"hang": hc["hang"], "dong": dc["dong"], "slug": slug(hc["hang"] + " " + dc["dong"]), "loai": dc.get("loai", "xe_con"),
                          "trang_hang": None, "phien_ban": [], "thong_so_chung": {}, "hinh_anh": [], "gia_tu": None,
                          "thieu": ["loi"], "trang_thai": "loi", "ghi_chu": [f"{type(e).__name__}: {str(e)[:200]}"]}
                # nếu lần này lỗi hoặc không thấy trang mà lần trước có dữ liệu → giữ bản lần trước, đánh dấu cũ
                if kq["trang_thai"] in ("loi", "khong_tim_thay_trang") or not kq["phien_ban"]:
                    c = next((x for x in cu.get("xe", []) if x.get("slug") == kq["slug"] and x.get("phien_ban")), None)
                    if c:
                        c = dict(c)
                        c["ghi_chu"] = (c.get("ghi_chu") or []) + [f"Lần cập nhật {ngay} không lấy được dữ liệu mới; đang hiển thị bản lần trước ({cu.get('cap_nhat', '?')})."]
                        c["trang_thai"] = "ban_cu"
                        kq = c
                ket_qua.append(kq)
                bao_cao["xe"].append({"hang": kq["hang"], "dong": kq["dong"], "trang_thai": kq["trang_thai"], "thieu": kq.get("thieu", []),
                                      "trang": kq.get("trang_hang"), "so_phien_ban": len(kq["phien_ban"]), "so_anh": len(kq["hinh_anh"]), "ghi_chu": kq["ghi_chu"]})
                print(f"[{kq['hang']} {kq['dong']}] {kq['trang_thai']} · {len(kq['phien_ban'])} phiên bản · {len(kq['hinh_anh'])} ảnh", flush=True)
            bao_cao["hang"][hc["hang"]] = loi_hang
    finally:
        br.dong()

    # giữ các hãng/dòng không chạy lần này (khi chạy lọc --hang/--dong)
    co = {(k["hang"], k["dong"]) for k in ket_qua}
    for x in cu.get("xe", []):
        if (x["hang"], x["dong"]) not in co:
            ket_qua.append(x)
    ket_qua.sort(key=lambda x: (x.get("gia_tu") is None, x.get("gia_tu") or 0))
    out = {"cap_nhat": ngay, "nguon": "Trang chính hãng của từng hãng; mỗi giá có địa chỉ nguồn riêng.",
           "cong_thuc_lan_banh": cfg["lephi"]["ghi_chu"], "xe": ket_qua}
    with open(os.path.join(DATA, "xe_chi_tiet.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    tong = {}
    for x in bao_cao["xe"]:
        tong[x["trang_thai"]] = tong.get(x["trang_thai"], 0) + 1
    bao_cao["tong_hop"] = tong
    with open(os.path.join(DATA, "xe_bao_cao.json"), "w", encoding="utf-8") as f:
        json.dump(bao_cao, f, ensure_ascii=False, indent=1)
    print("TỔNG HỢP:", tong)
    sm = os.environ.get("GITHUB_STEP_SUMMARY")
    if sm:
        with open(sm, "a", encoding="utf-8") as f:
            f.write("### Lấy dữ liệu xe\n" + "\n".join(f"- {k}: {v}" for k, v in tong.items()) + "\n")
            for h, l in bao_cao["hang"].items():
                for e in l:
                    f.write(f"- ⚠ {h}: {e}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
