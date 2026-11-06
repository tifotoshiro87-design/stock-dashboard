"""nen_sach.py — làm sạch chuỗi nến cổ phiếu trước khi vẽ biểu đồ/tính chỉ báo.

Lý do: Yahoo trả thêm một nến "giữ giá cũ" (khối lượng 0, mở = cao = thấp = đóng) cho mỗi ngày nghỉ lễ/không giao dịch,
và thỉnh thoảng có một nến nhiễu lệch hẳn rồi quay lại ngay hôm sau (ví dụ HDB 18/12/2025: +29,7% rồi -19,2%).
Các nến này làm EMA/RSI/MACD và đường trung bình khối lượng sai.

Quy tắc (chỉ bỏ, không bao giờ tự điền hay sửa số):
  1. Bỏ nến khối lượng 0 mà giá phẳng (ngày không có giao dịch thật).
  2. Bỏ nến nhiễu một phiên: đóng cửa lệch hơn 20% so với phiên trước đó nhưng phiên kế tiếp lại quay về trong 8% quanh
     giá trước (biên độ tối đa HOSE là 7%, HNX 10% nên lệch trên 20% rồi quay lại không phải giao dịch thật).
  3. Bỏ ngày trùng, sắp xếp theo ngày.
Dùng:  python nen_sach.py data/prices.json   (làm sạch file có sẵn, ghi kèm thống kê vào meta.lam_sach)
"""
import json
import sys


def lam_sach_nen(nen):
    """Trả về (nen_sach, bao_cao). bao_cao = {'nghi_le': số nến ngày nghỉ đã bỏ, 'nhieu': [ngày nến nhiễu đã bỏ]}."""
    thay, seen, nghi = [], set(), 0
    for x in sorted(nen or [], key=lambda z: z["t"]):
        if x["t"] in seen:
            continue
        seen.add(x["t"])
        if not x.get("v") and x["o"] == x["h"] == x["l"] == x["c"]:
            nghi += 1
            continue
        thay.append(x)
    kept, nhieu = [], []
    for i, x in enumerate(thay):
        if kept and i + 1 < len(thay):
            prev, nxt = kept[-1]["c"], thay[i + 1]["c"]
            if prev and abs(x["c"] / prev - 1) > 0.20 and abs(nxt / prev - 1) < 0.08:
                nhieu.append(x["t"])
                continue
        kept.append(x)
    return kept, {"nghi_le": nghi, "nhieu": nhieu}


def lam_sach_file(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        d = json.load(f)
    tong_nghi, nhieu = 0, {}
    for s in d.get("stocks", []):
        s["candles"], bc = lam_sach_nen(s.get("candles"))
        tong_nghi += bc["nghi_le"]
        if bc["nhieu"]:
            nhieu[s["symbol"]] = bc["nhieu"]
    phien = max((s["candles"][-1]["t"] for s in d["stocks"] if s["candles"]), default=None)
    d["meta"]["latest_session"] = phien
    d["meta"]["lam_sach"] = {"nghi_le_da_bo": tong_nghi, "nen_nhieu_da_bo": nhieu,
                              "ghi_chu": "Bỏ nến ngày nghỉ (khối lượng 0, giá phẳng) và nến nhiễu một phiên; không sửa số liệu nào."}
    with open(duong_dan, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    return tong_nghi, nhieu


if __name__ == "__main__":
    n, nh = lam_sach_file(sys.argv[1])
    print("đã bỏ", n, "nến ngày nghỉ;", "nến nhiễu:", nh)
