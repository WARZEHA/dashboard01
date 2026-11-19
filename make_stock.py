"""สร้างข้อมูลสต็อกจำลอง (stock.json) และไฟล์ data.js ให้ index.html ใช้

ทุกค่าในสต็อก (จำนวนคงเหลือ ต้นทุน วันหมดอายุ) เป็นข้อมูลสมมติ
ใช้ seed คงที่ รันซ้ำได้ผลเหมือนเดิม

วิธีรัน:  python make_stock.py
"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
AS_OF = date(2026, 11, 19)
SEED = 2026

# จำนวนรายการในแต่ละสถานะ (รวม 100)
N_OUT = 4        # หมดสต็อก
N_BELOW = 13     # ต่ำกว่าจุดสั่งซื้อ
N_NEAR = 12      # ใกล้จุดสั่งซื้อ (ไม่เกิน 1.5 เท่า)
N_EXPIRING = 8   # หมดอายุภายใน 90 วัน

# ต้นทุนต่อหน่วย (บาท) ตามหน่วยนับ
COST_RANGE = {
    "tablet": (0.4, 6.0),
    "capsule": (0.8, 8.0),
    "bottle": (25.0, 120.0),
    "tube": (30.0, 110.0),
    "inhaler": (180.0, 380.0),
    "sachet": (3.0, 7.0),
}
# ยาที่ราคาสูงกว่าปกติ
COST_OVERRIDE = {
    "CELE200": 12.0, "CLOP75": 9.5, "ROSU10": 11.0, "FEXO180": 10.0,
    "MONT10": 14.0, "ATOR20": 7.5, "SERT50": 8.0, "FLUCO150": 18.0,
    "AMCLAV875": 16.0, "BUDE-INH": 360.0, "FLUTI-NS": 240.0,
}


def main():
    rng = random.Random(SEED)
    catalog = json.loads((HERE / "drugs.json").read_text(encoding="utf-8"))
    items = catalog["items"]

    order = items[:]
    rng.shuffle(order)
    status_of = {}
    for i, it in enumerate(order):
        if i < N_OUT:
            status_of[it["sku"]] = "out"
        elif i < N_OUT + N_BELOW:
            status_of[it["sku"]] = "below"
        elif i < N_OUT + N_BELOW + N_NEAR:
            status_of[it["sku"]] = "near"
        else:
            status_of[it["sku"]] = "ok"

    in_stock = [it["sku"] for it in order if status_of[it["sku"]] != "out"]
    expiring = set(rng.sample(in_stock, N_EXPIRING))

    stock = []
    for it in items:
        sku, rl = it["sku"], it["reorder_level"]
        st = status_of[sku]
        if st == "out":
            qty = 0
        elif st == "below":
            qty = max(1, round(rl * rng.uniform(0.15, 0.95)))
            qty = min(qty, rl - 1)
        elif st == "near":
            qty = round(rl * rng.uniform(1.0, 1.5))
        else:
            qty = round(rl * rng.uniform(1.6, 4.0))

        lo, hi = COST_RANGE[it["unit"]]
        cost = COST_OVERRIDE.get(sku, rng.uniform(lo, hi))
        cost = round(cost, 2) if cost < 10 else round(cost)

        if sku in expiring:
            days = rng.randint(12, 88)
        else:
            days = rng.randint(150, 900)
        expiry = AS_OF + timedelta(days=days)

        stock.append({
            "sku": sku,
            "on_hand": qty,
            "unit_cost": cost,
            "expiry_date": expiry.isoformat(),
        })

    stock_doc = {
        "meta": {
            "title": "สต็อกจำลองของร้านยา",
            "note": "ข้อมูลสมมติทั้งหมด สร้างด้วย make_stock.py เพื่อใช้สาธิต dashboard",
            "as_of": AS_OF.isoformat(),
            "currency": "THB",
            "count": len(stock),
        },
        "items": stock,
    }
    (HERE / "stock.json").write_text(
        json.dumps(stock_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    # data.js ให้เปิด index.html ตรงจากไฟล์ได้ (เบราว์เซอร์ไม่ยอมให้ fetch ไฟล์ json ผ่าน file://)
    js = ("// สร้างอัตโนมัติจาก drugs.json + stock.json ด้วย make_stock.py ห้ามแก้มือ\n"
          "window.PHARMA_DATA = "
          + json.dumps({"catalog": catalog, "stock": stock_doc}, ensure_ascii=False)
          + ";\n")
    (HERE / "data.js").write_text(js, encoding="utf-8")

    counts = {s: list(status_of.values()).count(s) for s in ("ok", "near", "below", "out")}
    print("สถานะ:", counts, "| ใกล้หมดอายุ:", len(expiring))


if __name__ == "__main__":
    main()
