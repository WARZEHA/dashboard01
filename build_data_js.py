"""รวมไฟล์ JSON ในโฟลเดอร์นี้เป็น data.js เพื่อให้ดับเบิลคลิกเปิด index.html แล้วขึ้น dashboard ได้เลย

เบราว์เซอร์ไม่ยอมให้หน้าเว็บที่เปิดจากไฟล์ (file://) อ่านไฟล์ .json แต่ยอมโหลดไฟล์ .js
ไฟล์ JSON ยังเป็นต้นฉบับ ส่วน data.js เป็นแค่สำเนา

ต้องรันใหม่ทุกครั้งที่แก้ไฟล์ JSON:  python build_data_js.py
(clean_fix.py เรียกสคริปต์นี้ให้อัตโนมัติ)
"""
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
FILES = ['drugs.json', 'stock.json', 'dispense-log.json', 'data-issues.json']


def build():
    bundle = {}
    for name in FILES:
        path = HERE / name
        if path.exists():
            bundle[name] = json.loads(path.read_text(encoding='utf-8'))
    built = datetime.now().strftime('%Y-%m-%d %H:%M')
    js = ('// สร้างอัตโนมัติจากไฟล์ JSON ด้วย build_data_js.py เมื่อ ' + built + ' ห้ามแก้มือ\n'
          '// แก้ข้อมูลที่ไฟล์ .json แล้วรัน python build_data_js.py ใหม่\n'
          'window.PHARMA_JSON = ' + json.dumps(bundle, ensure_ascii=False, separators=(',', ':')) + ';\n'
          'window.PHARMA_JSON_BUILT = ' + json.dumps(built) + ';\n')
    (HERE / 'data.js').write_text(js, encoding='utf-8')
    print(f'data.js: {", ".join(bundle)} ({len(js) // 1024} KB)')


if __name__ == '__main__':
    build()
