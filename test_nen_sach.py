"""Kiểm thử offline cho nen_sach.py. Chạy: python test_nen_sach.py"""
from nen_sach import lam_sach_nen

def n(t,o,h,l,c,v): return {"t":t,"o":o,"h":h,"l":l,"c":c,"v":v}

# 1. nến ngày nghỉ (v=0, phẳng) bị bỏ; nến v=0 nhưng giá không phẳng thì giữ
d=[n("2026-01-01",10,10,10,10,100),n("2026-01-02",10,10.5,9.8,10.2,200),n("2026-01-03",10.2,10.2,10.2,10.2,0),n("2026-01-04",10.2,10.4,10,10.3,0)]
k,b=lam_sach_nen(d); assert [x["t"] for x in k]==["2026-01-01","2026-01-02","2026-01-04"] and b["nghi_le"]==1, (k,b)
# 2. nến nhiễu một phiên (HDB 18/12/2025) bị bỏ, phiên sau vẫn giữ
d=[n("2025-12-17",19,19.2,18.9,19.04,5),n("2025-12-18",24.6,24.7,24.5,24.69,5),n("2025-12-19",19.69,20,19.5,19.96,5),n("2025-12-22",20,20.2,19.8,20.1,5)]
k,b=lam_sach_nen(d); assert [x["t"] for x in k]==["2025-12-17","2025-12-19","2025-12-22"] and b["nhieu"]==["2025-12-18"], (k,b)
# 3. dịch chuyển giá vĩnh viễn (ví dụ chưa điều chỉnh chia tách) KHÔNG bị coi là nhiễu
d=[n("a",30,30,30,30,5),n("b",20,20,20,20,5),n("c",20.2,20.4,20,20.2,5),n("d",20.3,20.5,20.1,20.4,5)]
k,b=lam_sach_nen(d); assert len(k)==4 and not b["nhieu"], (k,b)
# 4. ngày trùng, sắp xếp, đầu vào rỗng
k,b=lam_sach_nen([n("2026-02-02",1,2,1,2,5),n("2026-02-01",1,2,1,1.5,5),n("2026-02-02",9,9,9,9,5)]); assert [x["t"] for x in k]==["2026-02-01","2026-02-02"] and k[1]["c"]==2
assert lam_sach_nen([])==([],{"nghi_le":0,"nhieu":[]}) and lam_sach_nen(None)[0]==[]
# 5. không sửa số: nến giữ lại giống hệt đầu vào
d=[n("2026-03-0%d"%i,10+i,11+i,9+i,10.5+i,100+i) for i in range(1,6)]; k,b=lam_sach_nen(d); assert k==d
print("TẤT CẢ ĐẠT")
