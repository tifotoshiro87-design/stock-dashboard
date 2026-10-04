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

# Thứ tự thử nguồn cho từng mã. Đổi thành ["yahoo", "vnstock"] nếu vnstock hay lỗi.
NGUON_UU_TIEN = ["yahoo"]  # vnstock đang bị PyPI cách ly (quarantine) từ 24/9/2026 nên không dùng

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


HAM_NGUON = {"vnstock": lay_vnstock, "yahoo": lay_yahoo}


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
                   "source": nguon_dung, "candles": nen,
                   "links": {"yahoo": f"https://finance.yahoo.com/quote/{ma}.VN"}})
    phien = max((s["candles"][-1]["t"] for s in ds if s["candles"]), default=None)
    meta = {"fetched_at": datetime.now(VN).strftime("%Y-%m-%d %H:%M"), "latest_session": phien,
            "unit": "nghìn đồng", "failed": loi, "sample": False,
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


# ===== Tin tự động theo từng mã (Google News RSS, miễn phí, không cần API key) =====
# Đây CHỈ là tin thô, chưa qua chọn lọc của người/AI — hiển thị riêng ở tab Tin tức,
# tách biệt với 3 mục (Chính sách/Pháp luật/Tin ngành) do lệnh "cập nhật" chọn lọc thủ công.
SO_TIN_MOI_MOI_MA = 3        # lấy tối đa mấy tin mới nhất cho mỗi mã
TONG_TIN_TOI_DA = 150        # tổng số tin giữ lại (mã mới hơn ưu tiên)

def lay_rss_ma(ma, ten):
    """Google News RSS tìm theo tên công ty. Lỗi/rỗng thì trả về danh sách rỗng, không chặn các mã khác."""
    q = quote(f'cổ phiếu {ten}' if len(ten) <= 4 else f'"{ten}"')  # chưa có tên công ty thì tìm theo mã
    url = f"https://news.google.com/rss/search?q={q}&hl=vi&gl=VN&ceid=VN:vi"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        cay = ET.fromstring(r.read())
    tin = []
    for item in cay.findall(".//item")[:SO_TIN_MOI_MOI_MA]:
        tieu_de = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        ngay_tho = item.findtext("pubDate")
        nguon_el = item.find("source")
        nguon = nguon_el.text.strip() if nguon_el is not None and nguon_el.text else ""
        if not tieu_de or not link:
            continue
        try:
            ngay = parsedate_to_datetime(ngay_tho).strftime("%Y-%m-%d") if ngay_tho else None
        except (TypeError, ValueError):
            ngay = None
        tin.append({"symbol": ma, "date": ngay, "title": tieu_de, "source": nguon, "url": link})
    return tin


def chuan_hoa_tieu_de(t):
    """Chuẩn hoá tiêu đề để so khớp tin trùng (khác hoa/thường, khác khoảng trắng)."""
    return re.sub(r"\s+", " ", t or "").strip().lower()


def lay_tin_tu_dong(danh_sach=None):
    tin_tho, loi = [], {}
    for ma, ten, _nhom, _san in (danh_sach or CO_PHIEU):
        try:
            tin_tho += thu_lai(lambda ma=ma, ten=ten: lay_rss_ma(ma, ten) or None, so_lan=2, cho=3)
        except Exception as e:  # noqa: BLE001
            loi[ma] = f"{type(e).__name__}: {e}"
        time.sleep(0.5)  # tránh gửi quá dồn dập tới Google News

    # Gộp tin trùng nhau: cùng 1 bài có thể ra ở nhiều mã (VD tin nhắc cả FPT lẫn CMG),
    # hoặc Google News trả về cùng bài với link theo dõi khác nhau -> so khớp theo TIÊU ĐỀ đã chuẩn hoá,
    # gộp các mã liên quan vào 1 dòng thay vì lặp lại nhiều lần.
    gop = {}
    for t in tin_tho:
        khoa = chuan_hoa_tieu_de(t["title"])
        if not khoa:
            continue
        if khoa in gop:
            if t["symbol"] not in gop[khoa]["symbols"]:
                gop[khoa]["symbols"].append(t["symbol"])
            if t["date"] and (not gop[khoa]["date"] or t["date"] < gop[khoa]["date"]):
                gop[khoa]["date"] = t["date"]  # giữ ngày sớm nhất bài này từng xuất hiện
        else:
            gop[khoa] = {"symbols": [t["symbol"]], "date": t["date"], "title": t["title"],
                         "source": t["source"], "url": t["url"]}
    tin_gop = sorted(gop.values(), key=lambda x: x["date"] or "", reverse=True)
    print(f"Tin tự động: {len(tin_tho)} tin thô -> {len(tin_gop)} sau khi gộp trùng, lỗi {len(loi)} mã: {list(loi)[:5]}")
    return {"fetched_at": datetime.now(VN).strftime("%Y-%m-%d %H:%M"), "failed": loi,
            "items": tin_gop[:TONG_TIN_TOI_DA]}


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
    # Tin tự động: chỉ ghi đè mục "auto" trong news.json, GIỮ NGUYÊN policy/law/industry
    # (những mục đó do lệnh "cập nhật" chọn lọc thủ công, script không được đụng vào).
    tin_cu = doc_json("news.json", {"meta": {"updated_at": None}, "policy": [], "law": [], "industry": {}})
    tin_cu["auto"] = lay_tin_tu_dong(CO_PHIEU + them)
    (THU_MUC / "news.json").write_text(
        json.dumps(tin_cu, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Xong. Xem data/prices.json (meta.failed) để biết mã nào lỗi.")


if __name__ == "__main__":
    main()
