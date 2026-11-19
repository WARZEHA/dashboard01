"""คลีนข้อมูลรอบที่ 2 ต่อจากที่คลีนเองไว้ใน cleaned-v1/

อ่าน:   cleaned-v1/drugs_update.json, cleaned-v1/stock (1).json, cleaned-v1/dispense-log (1).json
เขียน:  drugs.json, stock.json, dispense-log.json, data-issues.json

หลักการ
- ไม่เดาค่าที่ไม่มีหลักฐาน: แถวแบบนั้นติดธง review.status = "needs_review"
  dashboard ต้องไม่เอาแถวที่ needs_review ไปคำนวณ
- ค่าที่อนุมานได้จากหลักฐานในข้อมูล ติดธง review.status = "inferred" พร้อมเหตุผล
- ค่าเดิมก่อนแก้เก็บไว้ในช่อง original_* เสมอ
- ทุกการเปลี่ยนแปลงถูกบันทึกใน data-issues.json

วิธีรัน:  python clean_fix.py
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE / 'cleaned-v1'
CLEANED_ON = '2026-11-19'


def load(name):
    return json.loads((SRC / name).read_text(encoding='utf-8'))


def save(name, doc):
    (HERE / name).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


drugs = load('drugs_update.json')
stock = load('stock (1).json')
log = load('dispense-log (1).json')
issues = []


def note(file, row_id, action, detail):
    issues.append({'file': file, 'id': row_id, 'action': action, 'detail': detail})


def find(items, key, value):
    hit = [x for x in items if x[key] == value]
    assert len(hit) == 1, (key, value, len(hit))
    return hit[0]


S, L = stock['items'], log['items']
catalog = {d['sku'] for d in drugs['items']}

# ---------- 1) เอาแถว VITE400 กลับมา (ตอนนี้บัญชียามี VITE400 แล้ว) ----------
assert 'VITE400' in catalog
if not any(x['stock_id'] == 'S040' for x in S):
    S.append({'stock_id': 'S040', 'sku': 'VITE400', 'lot': 'VE2506', 'received_date': '2026-06-15',
              'expiry': '2028-05-31', 'qty_on_hand': 120, 'unit_cost': 2.5, 'status': 'active'})
    note('stock.json', 'S040', 'restored', 'คืนแถวสต็อก Tocopherol 400 IU ล็อต VE2506 เพราะบัญชียาเวอร์ชัน 2.0 มี VITE400 แล้ว')
if not any(x['dispense_id'] == 'D0072' for x in L):
    L.append({'dispense_id': 'D0072', 'datetime': '2026-10-18T14:30:00+07:00', 'sku': 'VITE400', 'lot': 'VE2506',
              'qty': 30, 'patient_code': 'PT-0032', 'pharmacist_code': 'RX-01', 'type': 'dispense', 'incident_ref': None})
    note('dispense-log.json', 'D0072', 'restored', 'คืนรายการจ่าย VITE400 30 แคปซูล เพราะบัญชียามี VITE400 แล้ว')

# ---------- 2) S027 จำนวนติดลบ: ไม่รู้ค่าจริง -> กักไว้รอตรวจนับ ----------
x = find(S, 'stock_id', 'S027')
x['original_qty_on_hand'] = -20
x['status'] = 'quarantine'
x['review'] = {'status': 'needs_review',
               'reason': 'ค่าเดิม -20 ซึ่งเป็นไปไม่ได้ และล็อต CT2509 ไม่มีการจ่ายในบันทึกเลย จึงไม่รู้ค่าจริง ต้องตรวจนับของจริง'}
note('stock.json', 'S027', 'quarantined', 'เดิมแก้จาก -20 เป็น 20 ซึ่งเป็นการเดา เปลี่ยนเป็น quarantine และเก็บค่าเดิมไว้')

for sid, reason in [('S007', 'วันหมดอายุ (2026-03-31) อยู่ก่อนวันรับเข้า (2026-09-14) ต้องตรวจฉลากของจริง'),
                    ('S022', 'ไม่มีวันหมดอายุ ต้องตรวจฉลากของจริง')]:
    x = find(S, 'stock_id', sid)
    assert x['status'] == 'quarantine'
    x['review'] = {'status': 'needs_review', 'reason': reason}
    note('stock.json', sid, 'flagged', 'เพิ่มเหตุผลที่กักไว้ในช่อง review')

# ---------- 3) ล็อตที่ตัดทิ้ง: เก็บจำนวนที่ตัดทิ้งไว้ ----------
for sid, qty in [('S002', 4), ('S037', 3), ('S004', 0)]:
    x = find(S, 'stock_id', sid)
    assert x['status'] == 'written_off'
    x['written_off_qty'] = qty
    note('stock.json', sid, 'added_field', f'เพิ่ม written_off_qty = {qty} (จำนวนคงเหลือก่อนตัดทิ้ง จากไฟล์ดิบ)')

# ---------- 4) ล็อตที่หมดแล้วแต่ยัง active ----------
x = find(S, 'stock_id', 'S010')
if x['qty_on_hand'] == 0 and x['status'] == 'active':
    x['status'] = 'depleted'
    note('stock.json', 'S010', 'status_changed', 'คงเหลือ 0 จึงเปลี่ยนสถานะจาก active เป็น depleted')

# ---------- 5) D0045: Amlodipine ใช้ล็อตของ Losartan ----------
x = find(L, 'dispense_id', 'D0045')
x['original_lot'] = x['lot']
x['lot'] = 'AM2502'
x['review'] = {'status': 'inferred',
               'reason': 'LS2505 เป็นล็อตของ Losartan ส่วน Amlodipine มีล็อต AM2502 กับ AM2508 '
                         'และวันเดียวกัน (D0048) จ่าย Amlodipine จากล็อต AM2502 จึงอนุมานว่าเป็น AM2502'}
note('dispense-log.json', 'D0045', 'inferred', 'เปลี่ยนล็อต LS2505 -> AM2502 ตามหลักฐานการจ่ายวันเดียวกัน')

# ---------- 6) D0120: จำนวน 2.5 เม็ด ----------
x = find(L, 'dispense_id', 'D0120')
x['review'] = {'status': 'needs_review',
               'reason': 'จำนวน 2.5 เม็ดเป็นไปไม่ได้สำหรับ Loratadine 10 mg รายการอื่นจ่าย 6–30 เม็ด ไม่มีหลักฐานว่าค่าจริงคืออะไร'}
note('dispense-log.json', 'D0120', 'flagged', 'จำนวน 2.5 ไม่ใช่จำนวนเต็ม ติดธงรอตรวจ ไม่นำไปคำนวณ')

# ---------- 7) D0149: วันที่อยู่นอกช่วงข้อมูล ----------
x = find(L, 'dispense_id', 'D0149')
x['review'] = {'status': 'needs_review',
               'reason': 'วันที่ 2026-11-05 อยู่หลังวันที่ของข้อมูล (2026-11-02) และนอกช่วง 3 ต.ค.–1 พ.ย. '
                         'รหัสเรียงตามเวลา จึงต้องอยู่หลัง D0148 (1 พ.ย. 13:50) แต่ระบุวันจริงไม่ได้'}
note('dispense-log.json', 'D0149', 'flagged', 'วันที่นอกช่วง ติดธงรอตรวจ ไม่นำไปคำนวณ')

# ---------- 8) รายการ void: ใช้รูปแบบเดียวกัน ----------
for did in ('D0030', 'D0093'):
    x = find(L, 'dispense_id', did)
    assert x['type'] == 'void'
    x['original_qty'] = x['qty']
    x['qty'] = 0
    x['voids'] = None
    x['review'] = {'status': 'needs_review',
                   'reason': 'เป็น void แต่ไม่พบรายการจ่ายที่ถูกยกเลิก (ผู้ป่วยรายนี้ไม่มีการจ่ายยาตัวนี้ก่อนหน้า) '
                             'ถ้ารู้ว่ายกเลิกรายการไหน ให้ใส่รหัสในช่อง voids'}
    note('dispense-log.json', did, 'normalized', f'void: qty {x["original_qty"]} -> 0 (เก็บค่าเดิมใน original_qty) และเพิ่มช่อง voids')

# ---------- เรียงและใส่ meta ----------
S.sort(key=lambda r: r['stock_id'])
L.sort(key=lambda r: r['dispense_id'])

stock['meta'].update({
    'cleaned': CLEANED_ON,
    'status_values': {'active': 'ขายได้', 'depleted': 'หมดแล้ว', 'quarantine': 'กักไว้ ห้ามจ่าย รอตรวจ',
                      'written_off': 'ตัดทิ้งแล้ว (written_off_qty = จำนวนที่ตัดทิ้ง)'},
    'review_note': 'แถวที่มี review.status = needs_review ต้องตรวจก่อนใช้ ห้ามนำไปคำนวณ',
})
log['meta'].update({
    'cleaned': CLEANED_ON,
    'type_values': {'dispense': 'จ่ายยา', 'void': 'ยกเลิก (qty = 0, voids = รหัสรายการที่ถูกยกเลิก)'},
    'review_note': 'แถวที่มี review.status = needs_review ห้ามนำไปคำนวณ ส่วน inferred ใช้ได้แต่ควรยืนยัน',
})
drugs['meta']['cleaned'] = CLEANED_ON

save('drugs.json', drugs)
save('stock.json', stock)
save('dispense-log.json', log)
save('data-issues.json', {'meta': {'title': 'บันทึกการคลีนข้อมูลรอบที่ 2', 'cleaned': CLEANED_ON,
                                   'source': 'cleaned-v1/'}, 'items': issues})
print(f'stock {len(S)} แถว · dispense {len(L)} แถว · บันทึก {len(issues)} รายการ')

# อัปเดต data.js ให้ดับเบิลคลิกเปิด dashboard ได้ทันที
import build_data_js  # noqa: E402
build_data_js.build()
