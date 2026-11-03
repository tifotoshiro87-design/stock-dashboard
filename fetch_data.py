# -*- coding: utf-8 -*-
"""
fetch_data.py - Lấy giá 16 mã cổ phiếu + số liệu vĩ mô quốc tế, ghi ra data/*.json
Chạy: python fetch_data.py
Nguyên tắc: không bịa số liệu. Không lấy được thì để null / ghi vào danh sách lỗi.
"""
import json
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

THU_MUC = Path(__file__).parent / "data"
THU_MUC.mkdir(exist_ok=True)
VN = timezone(timedelta(hours=7))

# Thứ tự thử nguồn cho từng mã: Yahoo trước (đủ sàn HOSE), KBS dự phòng (Yahoo không có sàn HNX).
# vnstock không dùng: đang bị PyPI cách ly (quarantine) từ 24/9/2026, nên gọi thẳng API KBS (hàm lay_kbs).
NGUON_UU_TIEN = ["yahoo", "kbs"]

# (mã, tên đầy đủ, nhóm ngành, sàn)
CO_PHIEU = [
    ("VCB", "NH TMCP Ngoại thương Việt Nam", "Ngân hàng", "HOSE"),
    ("VPB", "NH TMCP Việt Nam Thịnh Vượng", "Ngân hàng", "HOSE"),
    ("HDB", "NH TMCP Phát triển TP.HCM", "Ngân hàng", "HOSE"),
    ("MWG", "CTCP Đầu tư Thế Giới Di Động", "Công nghệ thông tin", "HOSE"),
    ("MSN", "CTCP Tập đoàn Masan", "Hỗn hợp", "HOSE"),
    ("DGW", "CTCP Thế Giới Số", "Công nghệ thông tin", "HOSE"),
    ("PNJ", "CTCP Vàng bạc Đá quý Phú Nhuận", "Vàng bạc trang sức", "HOSE"),
    ("GVR", "Tập đoàn Công nghiệp Cao su Việt Nam", "Xây dựng – Đầu tư công", "HOSE"),
    ("PHR", "CTCP Cao su Phước Hòa", "Xây dựng – Đầu tư công", "HOSE"),
    ("FPT", "CTCP FPT", "Công nghệ thông tin", "HOSE"),
    ("CMG", "CTCP Tập đoàn Công nghệ CMC", "Công nghệ thông tin", "HOSE"),
    ("VCG", "Tổng CTCP XNK và Xây dựng Việt Nam (Vinaconex)", "Xây dựng – Đầu tư công", "HOSE"),
    ("HHV", "CTCP Đầu tư Hạ tầng Giao thông Đèo Cả", "Xây dựng – Đầu tư công", "HOSE"),
    ("LCG", "CTCP Lizen", "Xây dựng – Đầu tư công", "HOSE"),
    ("FCN", "CTCP FECON", "Xây dựng – Đầu tư công", "HOSE"),
    ("CTD", "CTCP Xây dựng Coteccons", "Xây dựng – Đầu tư công", "HOSE"),
    ("HPG", "CTCP Tập đoàn Hòa Phát", "Thép", "HOSE"),
    ("HSG", "CTCP Tập đoàn Hoa Sen", "Thép", "HOSE"),
    ("NKG", "CTCP Thép Nam Kim", "Thép", "HOSE"),
    # --- Bổ sung 1/11/2026: 7 nhóm ngành mới (bỏ qua mã đã có: GVR, PHR, MWG, DGW, MSN, PNJ, BSR, GAS) ---
    ("SSI", "CTCP Chứng khoán SSI", "Chứng khoán", "HOSE"),
    ("VND", "CTCP Chứng khoán VNDIRECT", "Chứng khoán", "HOSE"),
    ("VCI", "CTCP Chứng khoán Vietcap", "Chứng khoán", "HOSE"),
    ("HCM", "CTCP Chứng khoán TP.HCM (HSC)", "Chứng khoán", "HOSE"),
    ("SHS", "CTCP Chứng khoán Sài Gòn – Hà Nội", "Chứng khoán", "HNX"),
    ("FTS", "CTCP Chứng khoán FPT", "Chứng khoán", "HOSE"),
    ("BSI", "CTCP Chứng khoán BIDV", "Chứng khoán", "HOSE"),
    ("MBS", "CTCP Chứng khoán MB", "Chứng khoán", "HNX"),
    ("CTS", "CTCP Chứng khoán Ngân hàng Công thương Việt Nam", "Chứng khoán", "HOSE"),
    ("AGR", "CTCP Chứng khoán Agribank", "Chứng khoán", "HOSE"),
    ("KDH", "CTCP Đầu tư và Kinh doanh Nhà Khang Điền", "Bất động sản dân dụng", "HOSE"),
    ("NLG", "CTCP Đầu tư Nam Long", "Bất động sản dân dụng", "HOSE"),
    ("PDR", "CTCP Phát triển Bất động sản Phát Đạt", "Bất động sản dân dụng", "HOSE"),
    ("DXG", "CTCP Tập đoàn Đất Xanh", "Bất động sản dân dụng", "HOSE"),
    ("CEO", "CTCP Tập đoàn C.E.O", "Bất động sản dân dụng", "HNX"),
    ("DIG", "Tổng CTCP Đầu tư Phát triển Xây dựng (DIC Corp)", "Bất động sản dân dụng", "HOSE"),
    ("NVL", "CTCP Tập đoàn Đầu tư Địa ốc No Va", "Bất động sản dân dụng", "HOSE"),
    ("HDG", "CTCP Tập đoàn Hà Đô", "Bất động sản dân dụng", "HOSE"),
    ("KBC", "Tổng Công ty Phát triển Đô thị Kinh Bắc – CTCP", "Bất động sản khu công nghiệp", "HOSE"),
    ("IDC", "Tổng Công ty IDICO – CTCP", "Bất động sản khu công nghiệp", "HNX"),
    ("SZC", "CTCP Sonadezi Châu Đức", "Bất động sản khu công nghiệp", "HOSE"),
    ("BCM", "Tổng Công ty Đầu tư và Phát triển Công nghiệp (Becamex IDC)", "Bất động sản khu công nghiệp", "HOSE"),
    ("VGC", "Tổng Công ty Viglacera – CTCP", "Bất động sản khu công nghiệp", "HOSE"),
    ("FRT", "CTCP Bán lẻ Kỹ thuật số FPT", "Bán lẻ & Tiêu dùng", "HOSE"),
    ("PET", "Tổng CTCP Dịch vụ Tổng hợp Dầu khí (PETROSETCO)", "Bán lẻ & Tiêu dùng", "HOSE"),
    ("PVD", "Tổng CTCP Khoan và Dịch vụ Khoan Dầu khí", "Dầu khí & Năng lượng", "HOSE"),
    ("PVS", "Tổng CTCP Dịch vụ Kỹ thuật Dầu khí Việt Nam", "Dầu khí & Năng lượng", "HNX"),
    ("PVT", "Tổng CTCP Vận tải Dầu khí", "Dầu khí & Năng lượng", "HOSE"),
    ("GEG", "CTCP Điện Gia Lai", "Dầu khí & Năng lượng", "HOSE"),
    ("REE", "CTCP Cơ điện lạnh (REE)", "Dầu khí & Năng lượng", "HOSE"),
    ("PC1", "CTCP Tập đoàn PC1", "Dầu khí & Năng lượng", "HOSE"),
    ("GMD", "CTCP Gemadept", "Cảng biển & Vận tải", "HOSE"),
    ("HAH", "CTCP Vận tải và Xếp dỡ Hải An", "Cảng biển & Vận tải", "HOSE"),
    ("VSC", "CTCP Tập đoàn Container Việt Nam (Viconship)", "Cảng biển & Vận tải", "HOSE"),
    ("VOS", "CTCP Vận tải Biển Việt Nam (VOSCO)", "Cảng biển & Vận tải", "HOSE"),
    ("VHC", "CTCP Vĩnh Hoàn", "Thủy sản & Xuất khẩu", "HOSE"),
    ("ANV", "CTCP Nam Việt", "Thủy sản & Xuất khẩu", "HOSE"),
    ("IDI", "CTCP Đầu tư và Phát triển Đa Quốc Gia I.D.I", "Thủy sản & Xuất khẩu", "HOSE"),
    ("FMC", "CTCP Thực phẩm Sao Ta", "Thủy sản & Xuất khẩu", "HOSE"),
    ("CMX", "CTCP Camimex Group", "Thủy sản & Xuất khẩu", "HOSE"),
]

# 14 tiêu chí vĩ mô: (ký hiệu, tên, có số liệu định lượng?)
TIEU_CHI = [
    ("A", "Lãi suất điều hành NHNN", True), ("B", "Tỷ giá USD/VND", True),
    ("C", "CPI/lạm phát", True), ("D", "Tiến độ giải ngân đầu tư công", True),
    ("E", "Thanh khoản/room tín dụng", True), ("F", "Chính sách/luật mới ảnh hưởng ngành", False),
    ("G", "Ổn định chính trị – xã hội", False), ("H", "Lãi suất Fed", True),
    ("I", "Chỉ số DXY", True), ("J", "Giá dầu thế giới", True),
    ("K", "Chứng khoán Mỹ (S&P500/Nasdaq)", True), ("L", "Căng thẳng thương mại/địa chính trị", False),
    ("M", "Dòng vốn khối ngoại", True), ("N", "Tin tức riêng của 5 nhóm ngành", False),
]
# Tiêu chí tự lấy được từ Yahoo: ký hiệu -> (mã Yahoo, đơn vị)
MACRO_TU_DONG = {"B": ("USDVND=X", "VND/USD"), "I": ("DX-Y.NYB", "điểm"),
                 "J": ("BZ=F", "USD/thùng (Brent)"), "K": ("^GSPC", "điểm (S&P 500)")}
THAM_KHAO = {"^IXIC": "Nasdaq", "CL=F": "Dầu WTI"}


def thu_lai(ham, so_lan=3, cho=2):
    """Gọi ham(); lỗi hoặc rỗng thì thử lại, chờ lâu dần."""
    loi = "Nguồn trả về rỗng"
    for i in range(so_lan):
        try:
            kq = ham()
            if kq is not None and len(kq) > 0:  # an toàn cho cả list lẫn pandas Series
                return kq
        except ImportError:  # thư viện tùy chọn chưa cài: bỏ qua ngay, không chờ thử lại
            raise
        except Exception as e:  # noqa: BLE001 - cần bắt mọi lỗi mạng/thư viện
            loi = f"{type(e).__name__}: {e}"
        time.sleep(cho * (i + 1))
    raise RuntimeError(loi)


def lay_yahoo(ma):
    """Yahoo trả giá bằng đồng -> chia 1000 thành nghìn đồng."""
    df = yf.Ticker(f"{ma}.VN").history(period="1y", interval="1d", auto_adjust=False)
    nen = []
    for ts, r in df.iterrows():
        if any(r[c] != r[c] for c in ("Open", "High", "Low", "Close")):  # bỏ dòng NaN
            continue
        vol = r["Volume"] if r["Volume"] == r["Volume"] else 0
        nen.append({"t": ts.strftime("%Y-%m-%d"), "o": round(r["Open"] / 1000, 2),
                    "h": round(r["High"] / 1000, 2), "l": round(r["Low"] / 1000, 2),
                    "c": round(r["Close"] / 1000, 2), "v": int(vol)})
    return nen


def lay_vnstock(ma):
    """vnstock (tùy chọn). Cú pháp thay đổi theo phiên bản; lỗi thì để nguồn kế tiếp xử lý."""
    from vnstock import Vnstock
    den = datetime.now(VN).date()
    tu = den - timedelta(days=400)
    df = Vnstock().stock(symbol=ma, source="VCI").quote.history(
        start=str(tu), end=str(den), interval="1D")
    nen = []
    for _, r in df.iterrows():
        he_so = 1000 if float(r["close"]) > 1000 else 1  # vnstock thường đã là nghìn đồng
        nen.append({"t": str(r["time"])[:10], "o": round(float(r["open"]) / he_so, 2),
                    "h": round(float(r["high"]) / he_so, 2), "l": round(float(r["low"]) / he_so, 2),
                    "c": round(float(r["close"]) / he_so, 2), "v": int(r["volume"])})
    return nen


# ---------- KBS (dự phòng cho mã Yahoo không có, chủ yếu sàn HNX) ----------
KBS_URL = "https://kbbuddywts.kbsec.com.vn/iis-server/investment/stocks/{ma}/data_day?sdate={tu}&edate={den}"
_KBS = {"da_kiem": False, "dat": False, "ket_qua": "chưa dùng"}   # kiểm tra đối chiếu với Yahoo đúng 1 lần mỗi lần chạy


def _ngay_kbs(v):
    """Chuẩn hóa ngày về YYYY-MM-DD; không hiểu được thì báo lỗi (không đoán)."""
    v = str(v).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", v):
        return v[:10]
    m = re.fullmatch(r"(\d{2})[/-](\d{2})[/-](\d{4}).*", v)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if re.fullmatch(r"\d{9,13}", v):
        sec = int(v) / (1000 if len(v) > 10 else 1)
        return datetime.fromtimestamp(sec, VN).strftime("%Y-%m-%d")
    raise ValueError(f"không hiểu định dạng ngày: {v[:20]}")


def phan_tich_kbs(js):
    """Tìm danh sách nến trong JSON (không phụ thuộc tên khóa), chuẩn hóa về nghìn đồng và kiểm tra hợp lý."""
    ds = js if isinstance(js, list) else next((v for v in (js or {}).values() if isinstance(v, list) and v and isinstance(v[0], dict)), None)
    if not ds:
        raise ValueError("KBS không trả về danh sách nến")

    def lay(r, *khoa):
        for k in khoa:
            if r.get(k) is not None:
                return r[k]
        raise KeyError(khoa[0])

    nen = []
    for r in ds:
        try:
            nen.append({"t": _ngay_kbs(lay(r, "t", "time", "date", "tradingDate")), "o": float(lay(r, "o", "open")), "h": float(lay(r, "h", "high")),
                        "l": float(lay(r, "l", "low")), "c": float(lay(r, "c", "close")), "v": int(float(lay(r, "v", "volume", "vol")))})
        except (KeyError, ValueError, TypeError):
            continue   # dòng thiếu/hỏng thì bỏ, không điền số
    nen.sort(key=lambda x: x["t"])
    if len(nen) < 30:
        raise ValueError(f"KBS chỉ có {len(nen)} nến hợp lệ (cần >= 30)")
    he_so = 1000 if sorted(x["c"] for x in nen)[len(nen) // 2] > 1000 else 1   # trung vị > 1000 => đơn vị đồng; giá cổ phiếu VN không có mã trên 1 triệu đồng
    for x in nen:
        for k in ("o", "h", "l", "c"):
            x[k] = round(x[k] / he_so, 2)
    if any(x["c"] <= 0 or x["h"] < x["l"] for x in nen):
        raise ValueError("KBS có nến sai (giá <= 0 hoặc cao < thấp)")
    tre = (datetime.now(VN).date() - datetime.strptime(nen[-1]["t"], "%Y-%m-%d").date()).days
    if tre > 15:
        raise ValueError(f"KBS dữ liệu cũ {tre} ngày")
    return nen


def _goi_kbs(ma):
    den = datetime.now(VN).date()
    url = KBS_URL.format(ma=ma, tu=(den - timedelta(days=400)).strftime("%d-%m-%Y"), den=den.strftime("%d-%m-%Y"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json", "Referer": "https://kbsec.com.vn/"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return phan_tich_kbs(json.loads(r.read().decode("utf-8", "ignore")))


def lay_kbs(ma):
    """Chỉ dùng KBS sau khi đối chiếu đúng với Yahoo ở mã VCB (cùng ngày, lệch <= 2%); không qua thì từ chối, không dùng số liệu chưa kiểm chứng."""
    if not _KBS["da_kiem"]:
        _KBS["da_kiem"] = True
        try:
            kbs, yh = {x["t"]: x["c"] for x in _goi_kbs("VCB")}, {x["t"]: x["c"] for x in lay_yahoo("VCB")}
            chung = sorted(set(kbs) & set(yh))
            if not chung:
                raise ValueError("không có ngày chung với Yahoo")
            lech = abs(kbs[chung[-1]] / yh[chung[-1]] - 1)
            if lech > 0.02:
                raise ValueError(f"giá VCB ngày {chung[-1]} lệch Yahoo {lech:.1%}")
            _KBS.update(dat=True, ket_qua=f"đạt đối chiếu VCB ({chung[-1]})")
        except Exception as e:  # noqa: BLE001
            _KBS["ket_qua"] = f"không đạt đối chiếu: {type(e).__name__}: {e}"[:160]
    if not _KBS["dat"]:
        raise RuntimeError("KBS " + _KBS["ket_qua"])
    return _goi_kbs(ma)


HAM_NGUON = {"vnstock": lay_vnstock, "yahoo": lay_yahoo, "kbs": lay_kbs}


def lay_von_hoa(ma):
    """Vốn hóa (đồng), dùng cho tab Tổng hợp. Yahoo không phải lúc nào cũng có cho mã .VN -> trả None thì để trống."""
    try:
        fi = yf.Ticker(f"{ma}.VN").fast_info
        mc = fi.get("market_cap") if hasattr(fi, "get") else getattr(fi, "market_cap", None)
        return float(mc) if mc else None
    except Exception:  # noqa: BLE001 - chỉ là dữ liệu phụ, lỗi thì bỏ qua, không chặn giá
        return None


def lay_gia(danh_sach=None):
    ds, loi = [], {}
    for ma, ten, nhom, san in (danh_sach or CO_PHIEU):
        nen, nguon_dung = [], None
        chi_tiet_loi = []
        for nguon in NGUON_UU_TIEN:  # fallback sang nguồn thứ hai
            try:
                nen = thu_lai(lambda: HAM_NGUON[nguon](ma), so_lan=2)
                nguon_dung = nguon
                break
            except Exception as e:  # noqa: BLE001
                chi_tiet_loi.append(f"{nguon}: {e}")
        if not nen:
            loi[ma] = " | ".join(chi_tiet_loi)
        print(("OK  " if nen else "LỖI"), ma, nguon_dung or loi[ma][:80])
        ds.append({"symbol": ma, "name": ten, "group": nhom, "exchange": san,
                   "source": nguon_dung, "candles": nen, "market_cap": lay_von_hoa(ma) if nen else None,
                   "links": {"yahoo": f"https://finance.yahoo.com/quote/{ma}.VN"}})
    phien = max((s["candles"][-1]["t"] for s in ds if s["candles"]), default=None)
    meta = {"fetched_at": datetime.now(VN).strftime("%Y-%m-%d %H:%M"), "latest_session": phien,
            "unit": "nghìn đồng", "failed": loi, "sample": False, "kbs": _KBS["ket_qua"],
            "disclaimer": "Chỉ mang tính tham khảo, không phải khuyến nghị đầu tư."}
    return {"meta": meta, "stocks": ds}


def doc_vn30_file():
    """Đọc vn30_list.json (cập nhật tay 2 lần/năm theo kỳ rà soát của HoSE: tháng 1 và tháng 7)."""
    try:
        return json.loads((Path(__file__).parent / "vn30_list.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        print("Không đọc được vn30_list.json:", e)
        return {}


def lay_vn30():
    """Danh sách thành phần VN30 lấy từ file vn30_list.json. Chưa có nguồn miễn phí ổn định cho điểm chỉ số VN30."""
    d = doc_vn30_file()
    mem = sorted({str(m).strip().upper() for m in d.get("members", []) if str(m).strip()})
    print("VN30:", len(mem), "mã thành phần (từ vn30_list.json), cập nhật:", d.get("updated"))
    return {"candles": [], "members": mem, "source": "vn30_list.json", "updated": d.get("updated"),
            "error_gia": "chưa có nguồn điểm chỉ số VN30", "error_thanh_phan": None if mem else "vn30_list.json trống"}


def doc_json(ten, mac_dinh):
    """Đọc file JSON cũ (giữ điểm số, số liệu nhập tay); lỗi thì dùng mặc định."""
    try:
        return json.loads((THU_MUC / ten).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return mac_dinh


def lay_macro():
    cu = doc_json("macro.json", {})
    tc = cu.get("criteria") or {
        k: {"name": t, "quantitative": dl, "previous": None, "current": None, "score": 0}
        for k, t, dl in TIEU_CHI}
    loi = {}

    def gia_dong_cua(ma_yf):
        h = yf.Ticker(ma_yf).history(period="1mo", interval="1d")["Close"].dropna()
        if len(h) < 2:
            raise ValueError("không đủ dữ liệu")
        return h

    for k, (ma_yf, don_vi) in MACRO_TU_DONG.items():
        try:
            h = thu_lai(lambda: gia_dong_cua(ma_yf), so_lan=2)
            nguon = f"Yahoo Finance ({ma_yf})"
            tc[k]["previous"] = {"value": round(float(h.iloc[-2]), 2), "unit": don_vi,
                                 "date": h.index[-2].strftime("%Y-%m-%d"), "source": nguon}
            tc[k]["current"] = {"value": round(float(h.iloc[-1]), 2), "unit": don_vi,
                                "date": h.index[-1].strftime("%Y-%m-%d"), "source": nguon}
        except Exception as e:  # noqa: BLE001
            loi[k] = str(e)
    tham_khao = {}
    for ma_yf, ten in THAM_KHAO.items():
        try:
            h = thu_lai(lambda: gia_dong_cua(ma_yf), so_lan=2)
            tham_khao[ma_yf] = {"name": ten, "value": round(float(h.iloc[-1]), 2),
                                "date": h.index[-1].strftime("%Y-%m-%d")}
        except Exception as e:  # noqa: BLE001
            loi[ma_yf] = str(e)
    return {"meta": {"fetched_at": datetime.now(VN).strftime("%Y-%m-%d %H:%M"), "failed": loi},
            "criteria": tc, "reference": tham_khao,
            "scored_at": cu.get("scored_at"), "summary": cu.get("summary"),
            "history": cu.get("history", []),
            "thresholds": cu.get("thresholds", {"sell": -4, "buy": 4})}


def lay_ten_cong_ty():
    """Tên công ty theo mã, lấy từ mục "names" trong vn30_list.json. Thiếu thì app hiện mã thay cho tên."""
    return {str(k).upper(): str(v) for k, v in doc_vn30_file().get("names", {}).items()}


def ghep_hon_hop(gia):
    """Thêm các mã VN30 chưa nằm trong 5 nhóm vào vùng "Hỗn hợp". Trả về danh sách mã đã thêm."""
    co = {m[0] for m in CO_PHIEU}
    ten = lay_ten_cong_ty()
    them = [(m, ten.get(m, m), "Hỗn hợp", "HOSE")
            for m in gia.get("vn30", {}).get("members", []) if m not in co]
    if them:
        g2 = lay_gia(them)
        gia["stocks"] += g2["stocks"]
        gia["meta"]["failed"].update(g2["meta"]["failed"])
    return them


def main():
    gia = lay_gia()
    gia["vn30"] = lay_vn30()
    them = ghep_hon_hop(gia)
    (THU_MUC / "prices.json").write_text(
        json.dumps(gia, ensure_ascii=False, indent=1), encoding="utf-8")
    (THU_MUC / "macro.json").write_text(
        json.dumps(lay_macro(), ensure_ascii=False, indent=1), encoding="utf-8")
    # Tin tức đã chuyển sang bot riêng fetch_news.py (data/tin.json); bot giá không còn đụng tới news.json.
    print("Xong. Xem data/prices.json (meta.failed) để biết mã nào lỗi.")


if __name__ == "__main__":
    main()
