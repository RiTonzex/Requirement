import urllib.parse

PALETTE = [
    ('#3b82f6', '#1d4ed8'),  # Blue
    ('#6366f1', '#4338ca'),  # Indigo
    ('#0ea5e9', '#0369a1'),  # Sky
    ('#10b981', '#047857'),  # Emerald
    ('#8b5cf6', '#6d28d9'),  # Violet
    ('#ec4899', '#be185d'),  # Pink
    ('#f59e0b', '#b45309'),  # Amber
    ('#14b8a6', '#0f766e'),  # Teal
    ('#f43f5e', '#be123c'),  # Rose
]


def generate_initial_avatar(name=None, user_id=None):
    """
    สร้าง Data URI ของรูปภาพ SVG รูปโปรไฟล์ตัวอักษรเริ่มต้น (Initial Letter Avatar)
    - รองรับทั้งภาษาไทยและภาษาอังกฤษ
    - มี Gradient Background สวยงามตามสีพาสเทลแบบโมเดิร์น
    - ทำงานได้ 100% โดยไม่ต้องพึ่งพาอินเทอร์เน็ตภายนอก
    """
    name_str = (name or '').strip()
    initial = name_str[0].upper() if name_str else 'U'

    # สุ่มเลือกสีอย่างสม่ำเสมอ (Deterministic) ตาม ID หรือผลรวมรหัสตัวอักษร
    if user_id and isinstance(user_id, int):
        color_index = user_id % len(PALETTE)
    elif name_str:
        color_index = sum(ord(c) for c in name_str) % len(PALETTE)
    else:
        color_index = 0

    bg1, bg2 = PALETTE[color_index]

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">'
        f'<defs>'
        f'<linearGradient id="avatarGrad" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" stop-color="{bg1}"/>'
        f'<stop offset="100%" stop-color="{bg2}"/>'
        f'</linearGradient>'
        f'</defs>'
        f'<rect width="200" height="200" rx="100" fill="url(#avatarGrad)"/>'
        f'<text x="50%" y="54%" font-family="Prompt, Kanit, Sarabun, -apple-system, sans-serif" '
        f'font-size="86" font-weight="700" fill="#ffffff" text-anchor="middle" dominant-baseline="middle">'
        f'{initial}'
        f'</text>'
        f'</svg>'
    )

    return f"data:image/svg+xml;utf8,{urllib.parse.quote(svg)}"
