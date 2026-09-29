# -*- coding: utf-8 -*-
"""
fetch_data.py - Lấy giá 17 mã cổ phiếu + số liệu vĩ mô quốc tế, ghi ra data/*.json
Chạy: python fetch_data.py
Nguyên tắc: không bịa số liệu. Không lấy được thì để null / ghi vào danh sách lỗi.
"""
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yfinance as yf

THU_MUC = Path(__file__).parent / "data"
THU_MUC.mkdir(exist_ok=True)
VN = timezone(timedelta(hours=7))

# Thứ tự thử nguồn cho từng mã. Đổi thành ["yahoo", "vnstock"] nếu vnstock hay lỗi.
NGUON_UU_TIEN = ["vnstock", "yahoo"]

# (mã, tên đầy đủ, nhóm ngành, sàn)
CO_PHIEU = [
    ("VCB", "NH TMCP Ngoại thương Việt Nam", "Ngân hàng", "HOSE"),
    ("VPB", "NH TMCP Việt Nam Thịnh Vượng", "Ngân hàng", "HOSE"),
    ("HDB", "NH TMCP Phát triển TP.HCM", "Ngân hàng", "HOSE"),
    ("MWG", "CTCP Đầu tư Thế Giới Di Động", "Công nghệ thông tin", "HOSE"),
    ("MSN", "CTCP Tập đoàn Masan", "Thép", "HOSE"),
    ("DGW", "CTCP Thế Giới Số", "Công nghệ thông tin", "HOSE"),
    ("PNJ", "CTCP Vàng bạc Đá quý Phú Nhuận", "Vàng bạc trang sức", "HOSE"),
    ("GVR", "Tập đoàn Công nghiệp Cao su Việt Nam", "Xây dựng – Đầu tư công", "HOSE"),
    ("PHR", "CTCP Cao su Phước Hòa", "Xây dựng – Đầu tư công", "HOSE"),
    ("IDC", "Tổng Công ty IDICO – CTCP", "Xây dựng – Đầu tư công", "HNX"),
    ("FPT", "CTCP FPT", "Công nghệ thông tin", "HOSE"),
    ("CMG", "CTCP Tập đoàn Công nghệ CMC", "Công nghệ thông tin", "HOSE"),
    ("VCG", "Tổng CTCP XNK và Xây dựng Việt Nam (Vinaconex)", "Xây dựng – Đầu tư công", "HOSE"),
    ("HHV", "CTCP Đầu tư Hạ tầng Giao thông Đèo Cả", "Xây dựng – Đầu tư công", "HOSE"),
    ("LCG", "CTCP Lizen", "Xây dựng – Đầu tư công", "HOSE"),
    ("FCN", "CTCP FECON", "Xây dựng – Đầu tư công", "HOSE"),
    ("CTD", "CTCP Xây dựng Coteccons", "Xây dựng – Đầu tư công", "HOSE"),
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
            if kq:
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


def lay_gia():
    ds, loi = [], {}
    for ma, ten, nhom, san in CO_PHIEU:
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


def main():
    (THU_MUC / "prices.json").write_text(
        json.dumps(lay_gia(), ensure_ascii=False, indent=1), encoding="utf-8")
    (THU_MUC / "macro.json").write_text(
        json.dumps(lay_macro(), ensure_ascii=False, indent=1), encoding="utf-8")
    if not (THU_MUC / "news.json").exists():  # tin tức do lệnh "cập nhật" ghi, script không đè
        (THU_MUC / "news.json").write_text(json.dumps(
            {"meta": {"updated_at": None}, "policy": [], "law": [], "industry": {}},
            ensure_ascii=False, indent=1), encoding="utf-8")
    print("Xong. Xem data/prices.json (meta.failed) để biết mã nào lỗi.")


if __name__ == "__main__":
    main()
